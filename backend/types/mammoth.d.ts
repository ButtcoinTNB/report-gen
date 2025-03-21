declare module 'mammoth' {
  interface ExtractResult {
    value: string;
    messages: Array<{
      type: string;
      message: string;
      [key: string]: any;
    }>;
  }

  interface Options {
    buffer?: Buffer;
    path?: string;
    [key: string]: any;
  }

  export function extractRawText(options: Options): Promise<ExtractResult>;
  export function convertToHtml(options: Options): Promise<ExtractResult>;
  export function convertToMarkdown(options: Options): Promise<ExtractResult>;
  export function embedStyleMap(options: Options): Promise<Buffer>;
  export function extractRawTextSync(options: Options): ExtractResult;
  export function convertToHtmlSync(options: Options): ExtractResult;
  export function convertToMarkdownSync(options: Options): ExtractResult;
  export function embedStyleMapSync(options: Options): Buffer;
} 