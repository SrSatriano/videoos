/// <reference types="vite/client" />

interface Window {
  videoOS?: {
    isDesktop: boolean;
    pickFiles: () => Promise<string[]>;
    pickFolder: () => Promise<string | null>;
    openPath: (targetPath: string) => Promise<boolean>;
  };
}
