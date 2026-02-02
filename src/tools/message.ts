/**
 * manage_message - Delete or edit bot's own messages
 * Gives the bot more "life" - can fix typos, delete spam, etc.
 */

// Store recent bot messages (chatId -> messageId[])
const recentMessages = new Map<number, number[]>();
const MAX_STORED = 20; // Keep last 20 messages per chat

/**
 * Record a message sent by bot
 */
export function recordBotMessage(chatId: number, messageId: number) {
  const messages = recentMessages.get(chatId) || [];
  messages.push(messageId);
  if (messages.length > MAX_STORED) {
    messages.shift();
  }
  recentMessages.set(chatId, messages);
}

/**
 * Get recent message IDs for a chat
 */
export function getRecentMessages(chatId: number): number[] {
  return recentMessages.get(chatId) || [];
}

// Callbacks (set from bot)
let deleteMessageCallback: ((chatId: number, messageId: number) => Promise<boolean>) | null = null;
let editMessageCallback: ((chatId: number, messageId: number, newText: string) => Promise<boolean>) | null = null;

export function setDeleteMessageCallback(cb: (chatId: number, messageId: number) => Promise<boolean>) {
  deleteMessageCallback = cb;
}

export function setEditMessageCallback(cb: (chatId: number, messageId: number, newText: string) => Promise<boolean>) {
  editMessageCallback = cb;
}

export const definition = {
  type: "function" as const,
  function: {
    name: "manage_message",
    description: "Delete or edit your own recent messages. Use to fix typos, remove spam, or clean up. Can only manage YOUR OWN messages from this conversation.",
    parameters: {
      type: "object",
      properties: {
        action: {
          type: "string",
          enum: ["delete_last", "delete_by_index", "edit_last"],
          description: "Action: delete_last (delete your last message), delete_by_index (delete by index, 0=oldest), edit_last (edit your last message)"
        },
        index: {
          type: "number",
          description: "For delete_by_index: which message to delete (0=oldest recent, -1=newest)"
        },
        new_text: {
          type: "string",
          description: "For edit_last: the new text for the message"
        },
      },
      required: ["action"],
    },
  },
};

export async function execute(
  args: { action: string; index?: number; new_text?: string },
  chatId: number
): Promise<{ success: boolean; output?: string; error?: string }> {
  const messages = recentMessages.get(chatId) || [];
  
  if (messages.length === 0) {
    return { success: false, error: 'No recent messages to manage' };
  }
  
  switch (args.action) {
    case 'delete_last': {
      if (!deleteMessageCallback) {
        return { success: false, error: 'Delete not configured' };
      }
      const msgId = messages[messages.length - 1];
      try {
        const ok = await deleteMessageCallback(chatId, msgId);
        if (ok) {
          messages.pop();
          recentMessages.set(chatId, messages);
          return { success: true, output: 'Deleted last message' };
        }
        return { success: false, error: 'Failed to delete (maybe already deleted or too old)' };
      } catch (e: any) {
        return { success: false, error: `Delete failed: ${e.message}` };
      }
    }
    
    case 'delete_by_index': {
      if (!deleteMessageCallback) {
        return { success: false, error: 'Delete not configured' };
      }
      let idx = args.index ?? -1;
      if (idx < 0) idx = messages.length + idx;
      if (idx < 0 || idx >= messages.length) {
        return { success: false, error: `Invalid index. Have ${messages.length} messages (0-${messages.length - 1})` };
      }
      const msgId = messages[idx];
      try {
        const ok = await deleteMessageCallback(chatId, msgId);
        if (ok) {
          messages.splice(idx, 1);
          recentMessages.set(chatId, messages);
          return { success: true, output: `Deleted message at index ${idx}` };
        }
        return { success: false, error: 'Failed to delete' };
      } catch (e: any) {
        return { success: false, error: `Delete failed: ${e.message}` };
      }
    }
    
    case 'edit_last': {
      if (!editMessageCallback) {
        return { success: false, error: 'Edit not configured' };
      }
      if (!args.new_text) {
        return { success: false, error: 'new_text required for edit' };
      }
      const msgId = messages[messages.length - 1];
      try {
        const ok = await editMessageCallback(chatId, msgId, args.new_text);
        if (ok) {
          return { success: true, output: 'Edited last message' };
        }
        return { success: false, error: 'Failed to edit (maybe too old or contains media)' };
      } catch (e: any) {
        return { success: false, error: `Edit failed: ${e.message}` };
      }
    }
    
    default:
      return { success: false, error: `Unknown action: ${args.action}` };
  }
}
