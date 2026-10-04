import { Component, type ErrorInfo, type ReactNode } from "react";

type Props = {
  children: ReactNode;
  fallback?: (retry: () => void) => ReactNode;
};

type State = {
  hasError: boolean;
};

// Evita que un error de render (o un chunk que ya no existe tras un deploy)
// deje la pestaña en blanco: React desmonta todo el árbol si nadie lo captura.
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ErrorBoundary capturó un error:", error, info);
  }

  retry = () => {
    this.setState({ hasError: false });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback(this.retry);
      }
      return (
        <div className="flex flex-col items-center justify-center py-20 text-center bg-base-200 rounded-lg border-2 border-dashed border-error/40">
          <div className="w-16 h-16 bg-error/10 rounded-full flex items-center justify-center mb-4">
            <i className="bx bx-error-circle text-2xl text-error"></i>
          </div>
          <h2 className="text-xl font-medium text-base-content/70 mb-2">
            Ocurrió un error al cargar este contenido
          </h2>
          <p className="text-base-content/50 max-w-sm mb-4">
            Puede deberse a una actualización reciente del sistema. Intenta
            recargar la página.
          </p>
          <button className="btn btn-success" onClick={() => window.location.reload()}>
            Recargar página
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
