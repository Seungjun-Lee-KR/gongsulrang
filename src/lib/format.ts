export function formatWon(n: number): string {
  if (n >= 100_000_000) {
    const eok = n / 100_000_000;
    const s = eok.toFixed(1).replace(/\.0$/, "");
    return `${s}억원`;
  }
  if (n >= 10_000) {
    const man = n / 10_000;
    const display =
      man === Math.floor(man) ? man.toLocaleString() : man.toFixed(1);
    return `${display}만원`;
  }
  return `${n.toLocaleString()}원`;
}
