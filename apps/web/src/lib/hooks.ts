import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';

/** True while the user steps by keyboard: state changes land instantly, without tweening. */
export const InstantContext = createContext(false);

export function useMediaQuery(query: string) {
  const [match, setMatch] = useState(() => typeof matchMedia !== 'undefined' && matchMedia(query).matches);
  useEffect(() => {
    const m = matchMedia(query);
    const on = () => setMatch(m.matches);
    on();
    m.addEventListener('change', on);
    return () => m.removeEventListener('change', on);
  }, [query]);
  return match;
}

export function useReducedMotion() {
  const query = '(prefers-reduced-motion: reduce)';
  const [reduce, setReduce] = useState(() => typeof matchMedia !== 'undefined' && matchMedia(query).matches);
  useEffect(() => {
    const m = matchMedia(query);
    const on = () => setReduce(m.matches);
    m.addEventListener('change', on);
    return () => m.removeEventListener('change', on);
  }, []);
  return reduce;
}

/**
 * Element width via ResizeObserver. Returns a callback ref so observation follows the element even
 * when it mounts later (e.g. ledger accounts that appear only after settlement).
 */
export function useWidth<T extends HTMLElement>() {
  const [width, setWidth] = useState(0);
  const ro = useRef<ResizeObserver | null>(null);
  const ref = useCallback((el: T | null) => {
    ro.current?.disconnect();
    ro.current = null;
    if (!el) return;
    setWidth(el.getBoundingClientRect().width);
    ro.current = new ResizeObserver(([e]) => setWidth(e.contentRect.width));
    ro.current.observe(el);
  }, []);
  useEffect(() => () => ro.current?.disconnect(), []);
  return [ref, width] as const;
}

export interface Route {
  view: 'arena' | 'theater' | 'evolution';
  t?: number;
  trace?: string;
}

function parse(hash: string): Route {
  const [path, query = ''] = hash.replace(/^#\/?/, '').split('?');
  const view = path === 'theater' || path === 'evolution' ? path : 'arena';
  const q = new URLSearchParams(query);
  const t = q.has('t') ? Number(q.get('t')) : undefined;
  return { view, t: Number.isInteger(t) ? t : undefined, trace: q.get('trace') ?? undefined };
}

export function format(r: Route) {
  const q = new URLSearchParams();
  if (r.t !== undefined && r.t >= 0) q.set('t', String(r.t));
  if (r.trace) q.set('trace', r.trace);
  const s = q.toString();
  return `#/${r.view}${s ? `?${s}` : ''}`;
}

export function useHashRoute() {
  const [route, setRoute] = useState(() => parse(location.hash));
  useEffect(() => {
    const on = () => setRoute(parse(location.hash));
    addEventListener('hashchange', on);
    return () => removeEventListener('hashchange', on);
  }, []);
  /** Replace (not push) for playback so the back button is not flooded with frames. */
  const replace = useCallback((r: Route) => {
    history.replaceState(null, '', format(r));
    setRoute(r);
  }, []);
  return [route, replace] as const;
}

/** Tween a number toward its target; instant under reduced motion. */
export function useTweened(target: number, duration = 420) {
  const reduced = useReducedMotion();
  const instant = useContext(InstantContext);
  const reduce = reduced || instant;
  const [value, setValue] = useState(target);
  const from = useRef(target);
  useEffect(() => {
    if (reduce || from.current === target) {
      from.current = target;
      setValue(target);
      return;
    }
    const start = performance.now();
    const a = from.current;
    let raf = 0;
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - p, 4);
      const v = a + (target - a) * eased;
      from.current = v;
      setValue(v);
      if (p < 1) raf = requestAnimationFrame(tick);
      else from.current = target;
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration, reduce]);
  return value;
}
