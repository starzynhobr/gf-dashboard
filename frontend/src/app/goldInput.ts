export function formatGoldInput(value: string): string {
  const digits = value.replace(/\D/g, "");
  return digits ? digits.replace(/\B(?=(\d{3})+(?!\d))/g, ".") : "";
}
