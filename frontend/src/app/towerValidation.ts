export function towerInteger(raw: string, label: string, minimum = 0): number {
  if (!/^\d+$/.test(raw.trim())) {
    throw new Error(`${label} deve ser um número inteiro ${minimum ? "maior que zero" : "não negativo"}.`);
  }
  const value = Number(raw);
  if (!Number.isSafeInteger(value) || value < minimum) {
    throw new Error(`${label} deve ser um número inteiro seguro ${minimum ? "maior que zero" : "não negativo"}.`);
  }
  return value;
}
