/**
 * memory - Long-term memory storage
 * Saves important info to MEMORY.md for future sessions
 */

import { readFileSync, writeFileSync, existsSync } from 'fs';
import { join } from 'path';

const MEMORY_FILE = 'MEMORY.md';

export const definition = {
  type: "function" as const,
  function: {
    name: "memory",
    description: "Long-term memory. Use to save important info (project context, decisions, todos) or read previous notes. Memory persists across sessions.",
    parameters: {
      type: "object",
      properties: {
        action: {
          type: "string",
          enum: ["read", "append", "clear"],
          description: "read: get all memory, append: add new entry, clear: reset memory"
        },
        content: {
          type: "string",
          description: "For append: text to add (will be timestamped automatically)"
        },
      },
      required: ["action"],
    },
  },
};

export function execute(
  args: { action: 'read' | 'append' | 'clear'; content?: string },
  cwd: string
): { success: boolean; output?: string; error?: string } {
  const memoryPath = join(cwd, MEMORY_FILE);
  
  try {
    switch (args.action) {
      case 'read': {
        if (!existsSync(memoryPath)) {
          return { success: true, output: '(memory is empty)' };
        }
        const content = readFileSync(memoryPath, 'utf-8');
        return { success: true, output: content || '(memory is empty)' };
      }
      
      case 'append': {
        if (!args.content) {
          return { success: false, error: 'Content required for append' };
        }
        
        const timestamp = new Date().toISOString().slice(0, 16).replace('T', ' ');
        const entry = `\n## ${timestamp}\n${args.content}\n`;
        
        let existing = '';
        if (existsSync(memoryPath)) {
          existing = readFileSync(memoryPath, 'utf-8');
        } else {
          existing = '# Agent Memory\n\nImportant context and notes from previous sessions.\n';
        }
        
        writeFileSync(memoryPath, existing + entry, 'utf-8');
        return { success: true, output: `Added to memory (${args.content.length} chars)` };
      }
      
      case 'clear': {
        const header = '# Agent Memory\n\nImportant context and notes from previous sessions.\n';
        writeFileSync(memoryPath, header, 'utf-8');
        return { success: true, output: 'Memory cleared' };
      }
      
      default:
        return { success: false, error: `Unknown action: ${args.action}` };
    }
  } catch (e: any) {
    return { success: false, error: e.message };
  }
}

/**
 * Get memory content for system prompt injection
 */
export function getMemoryForPrompt(cwd: string): string | null {
  const memoryPath = join(cwd, MEMORY_FILE);
  
  if (!existsSync(memoryPath)) {
    return null;
  }
  
  try {
    const content = readFileSync(memoryPath, 'utf-8');
    if (content.trim().length < 100) {
      return null;  // Too short, probably just header
    }
    
    // Limit to last ~2000 chars to not overflow context
    const maxLen = 2000;
    if (content.length > maxLen) {
      return '...(truncated)...\n' + content.slice(-maxLen);
    }
    return content;
  } catch {
    return null;
  }
}
