import { useEffect, useRef, useState } from "react";
export default function CountUp({
  value,
  decimals = 0,
}: {
  value: number;
  decimals?: number;
}) {
  const previous = useRef(value),
    [display, setDisplay] = useState(value);
  useEffect(() => {
    const start = performance.now(),
      from = previous.current;
    let frame = 0;
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setDisplay(value);
      previous.current = value;
      return;
    }
    const tick = (time: number) => {
      const t = Math.min((time - start) / 380, 1);
      setDisplay(from + (value - from) * (1 - Math.pow(1 - t, 3)));
      if (t < 1) frame = requestAnimationFrame(tick);
      else previous.current = value;
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value]);
  return (
    <span aria-label={value.toFixed(decimals)}>
      {display.toLocaleString("en-US", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      })}
    </span>
  );
}
