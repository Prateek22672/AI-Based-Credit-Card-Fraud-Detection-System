import { useEffect, useState } from "react";
import { ImageOff } from "lucide-react";
import { figureUrls } from "../../lib/api.js";

// Report figure: tries the API (/figures) then the synced static copy (/data/figures).
// Renders nothing (or a placeholder) when neither exists.
export default function Figure({ name, caption, placeholder = false, className = "", onMissing }) {
  const [idx, setIdx] = useState(0);
  const [failed, setFailed] = useState(false);
  const urls = figureUrls(name);

  useEffect(() => {
    setIdx(0);
    setFailed(false);
  }, [name]);

  useEffect(() => {
    if (failed) onMissing?.(name);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [failed]);

  if (failed) {
    if (!placeholder) return null;
    return (
      <figure className={`card overflow-hidden ${className}`}>
        <div className="flex h-44 flex-col items-center justify-center gap-2 bg-slate-50 text-muted">
          <ImageOff size={20} />
          <span className="text-[12px]">Figure not generated yet</span>
          <span className="font-mono text-[11px]">{name}.png</span>
        </div>
        {caption && <figcaption className="px-4 py-3 text-[12.5px] text-ink-2">{caption}</figcaption>}
      </figure>
    );
  }
  return (
    <figure className={`card overflow-hidden ${className}`}>
      <a href={urls[idx]} target="_blank" rel="noreferrer" className="block bg-white">
        <img
          src={urls[idx]}
          alt={caption || name}
          loading="lazy"
          className="w-full object-contain"
          onError={() => (idx + 1 < urls.length ? setIdx(idx + 1) : setFailed(true))}
        />
      </a>
      {caption && <figcaption className="border-t border-line px-4 py-3 text-[12.5px] text-ink-2">{caption}</figcaption>}
    </figure>
  );
}
