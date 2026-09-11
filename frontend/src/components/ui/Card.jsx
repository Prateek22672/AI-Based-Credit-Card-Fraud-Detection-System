export default function Card({ title, subtitle, actions, children, className = "", bodyClassName = "", noPad = false }) {
  return (
    <section className={`card ${className}`}>
      {(title || actions) && (
        <header className="flex flex-wrap items-start justify-between gap-3 px-5 pt-5 md:px-6 md:pt-5">
          <div className="min-w-0">
            {title && <h2 className="card-title">{title}</h2>}
            {subtitle && <p className="card-sub">{subtitle}</p>}
          </div>
          {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className={`${noPad ? "" : "card-pad"} ${title || actions ? (noPad ? "pt-4" : "pt-4!") : ""} ${bodyClassName}`}>{children}</div>
    </section>
  );
}

export function SectionTitle({ children, sub, className = "" }) {
  return (
    <div className={`mb-3 ${className}`}>
      <h2 className="text-[17px] font-semibold">{children}</h2>
      {sub && <p className="text-[13px] text-muted mt-0.5">{sub}</p>}
    </div>
  );
}
