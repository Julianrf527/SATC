export type Toast = {
  id: number;
  message: string;
  type: "success" | "error";
};

let toastHandler: ((t: Toast) => void) | null = null;

export const toastService = {
  setHandler: (fn: (t: Toast) => void) => {
    toastHandler = fn;
  },
  showToast: (toast: Toast) => {
    toastHandler?.(toast);
  },
};
