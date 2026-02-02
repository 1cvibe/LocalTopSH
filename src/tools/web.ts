/**
 * Web tools - Pattern: Action + Object
 * search_web (Z.AI primary, Tavily fallback), fetch_page
 */

interface SearchResult {
  title: string;
  url: string;
  content: string;
  date?: string;
}

// Z.AI Web Search API
async function searchZai(query: string, apiKey: string): Promise<SearchResult[]> {
  const response = await fetch('https://api.z.ai/v1/web-search', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      search_engine: 'search-prime',
      search_query: query,
      count: 5,
    }),
  });
  
  if (!response.ok) {
    throw new Error(`Z.AI error: ${response.status}`);
  }
  
  const data = await response.json();
  return (data.search_result || []).map((r: any) => ({
    title: r.title,
    url: r.link,
    content: r.content,
    date: r.publish_date,
  }));
}

// Tavily Search API (fallback)
async function searchTavily(query: string, apiKey: string): Promise<SearchResult[]> {
  const { tavily } = await import('@tavily/core');
  const client = tavily({ apiKey });
  const response = await client.search(query, { maxResults: 5 });
  
  return response.results.map((r: any) => ({
    title: r.title,
    url: r.url,
    content: r.content,
  }));
}

// ============ search_web ============
export const searchWebDefinition = {
  type: "function" as const,
  function: {
    name: "search_web",
    description: "Search the internet. USE IMMEDIATELY for: news, current events, external info, 'what is X?', prices, weather.",
    parameters: {
      type: "object",
      properties: {
        query: { type: "string", description: "Search query" },
      },
      required: ["query"],
    },
  },
};

export async function executeSearchWeb(
  args: { query: string },
  zaiApiKey?: string,
  tavilyApiKey?: string
): Promise<{ success: boolean; output?: string; error?: string }> {
  try {
    let results: SearchResult[];
    
    // Try Z.AI first (better structured results)
    if (zaiApiKey) {
      try {
        results = await searchZai(args.query, zaiApiKey);
      } catch (e) {
        console.log('[search] Z.AI failed, trying Tavily...');
        if (tavilyApiKey) {
          results = await searchTavily(args.query, tavilyApiKey);
        } else {
          throw e;
        }
      }
    } else if (tavilyApiKey) {
      results = await searchTavily(args.query, tavilyApiKey);
    } else {
      return { success: false, error: "No search API configured (ZAI_API_KEY or TAVILY_API_KEY)" };
    }
    
    if (!results.length) {
      return { success: true, output: "(no results)" };
    }
    
    const output = results.map((r, i) => {
      const date = r.date ? ` (${r.date})` : '';
      return `[${i + 1}] ${r.title}${date}\n${r.url}\n${r.content.slice(0, 400)}`;
    }).join('\n\n');
    
    return { success: true, output };
  } catch (e: any) {
    return { success: false, error: e.message };
  }
}

// ============ fetch_page ============
export const fetchPageDefinition = {
  type: "function" as const,
  function: {
    name: "fetch_page",
    description: "Fetch content from a URL.",
    parameters: {
      type: "object",
      properties: {
        url: { type: "string", description: "URL to fetch" },
      },
      required: ["url"],
    },
  },
};

export async function executeFetchPage(
  args: { url: string }
): Promise<{ success: boolean; output?: string; error?: string }> {
  try {
    const response = await fetch(args.url, {
      headers: { 'User-Agent': 'Mozilla/5.0 (compatible; Agent/1.0)' },
    });
    
    if (!response.ok) {
      return { success: false, error: `HTTP ${response.status}` };
    }
    
    const text = await response.text();
    return { success: true, output: text.slice(0, 50000) };
  } catch (e: any) {
    return { success: false, error: e.message };
  }
}
