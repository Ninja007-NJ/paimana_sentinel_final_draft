import type { ReactNode } from "react";

export function PageHeader({ 
  eyebrow, 
  title, 
  description, 
  actions 
}: { 
  eyebrow: string; 
  title: string; 
  description: string; 
  actions?: ReactNode 
}) {
  return (
    <header className="page-header command-center-header">
      <div className="header-main-content">
        <div className="eyebrow-wrapper">
          <span className="eyebrow">
            <span className="eyebrow-dot" />
            {eyebrow}
          </span>
        </div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  );
}

