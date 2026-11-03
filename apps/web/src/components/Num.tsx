import { useTweened } from '../lib/hooks';
import { fmt } from '../trace/narrate';

interface Props {
  value: number;
  signed?: boolean;
  /** Decimal places for non-integer values such as forecasts. */
  dp?: number;
  tone?: 'gain' | 'loss' | 'auto';
  className?: string;
}

/** Monospaced figure that eases between values. Integers stay integers while tweening. */
export function Num({ value, signed, dp, tone, className }: Props) {
  const v = useTweened(value);
  const shown = dp !== undefined ? v.toFixed(dp) : fmt(Math.round(v), signed);
  const t = tone === 'auto' ? (value > 0 ? 'gain' : value < 0 ? 'loss' : undefined) : tone;
  return (
    <span className={['num', t, className].filter(Boolean).join(' ')}>
      {dp !== undefined && signed && value > 0 ? '+' : ''}
      {shown}
    </span>
  );
}
