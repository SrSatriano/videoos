import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Erro de render no Video OS", error, info);
  }

  render() {
    if (!this.state.error) {
      return this.props.children;
    }

    return (
      <main className="fatal-error">
        <div>
          <AlertTriangle size={28} />
          <h1>Video OS encontrou um erro na interface</h1>
          <p>{this.state.error.message || "Falha inesperada ao renderizar a tela."}</p>
          <button onClick={() => window.location.reload()} type="button">
            <RotateCcw size={16} />
            Recarregar
          </button>
        </div>
      </main>
    );
  }
}
