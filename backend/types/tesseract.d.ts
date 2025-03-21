declare namespace Tesseract {
  interface WorkerOptions {
    logger?: (message: any) => void;
    errorHandler?: (error: any) => void;
    [key: string]: any;
  }

  interface RecognizeResult {
    data: {
      text: string;
      words: Array<{
        text: string;
        confidence: number;
        [key: string]: any;
      }>;
      [key: string]: any;
    };
    [key: string]: any;
  }

  interface Worker {
    recognize(image: Buffer | string): Promise<RecognizeResult>;
    terminate(): Promise<void>;
    [key: string]: any;
  }
}

declare module 'tesseract.js' {
  export function createWorker(language?: string | Tesseract.WorkerOptions): Promise<Tesseract.Worker>;
  export function createScheduler(): any;
  export const createWorkerUtils: any;
  export const PSM: { [key: string]: number };
  export const OEM: { [key: string]: number };
} 