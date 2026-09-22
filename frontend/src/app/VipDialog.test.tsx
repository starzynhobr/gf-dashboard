import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { VipDialog } from "./VipDialog";

afterEach(cleanup);

describe("VipDialog", () => {
  it("formats large gold values while preserving the numeric value on save", () => {
    const onSave = vi.fn();
    render(<VipDialog characterName="Sentry1" expiresAt={null} saving={false} error={null} onClose={vi.fn()} onSave={onSave} />);

    const input = screen.getByLabelText("Valor pago em gold");
    expect(input).toHaveValue("100.000");

    fireEvent.change(input, { target: { value: "12500000" } });
    expect(input).toHaveValue("12.500.000");

    fireEvent.click(screen.getByRole("button", { name: "Ativar VIP" }));
    expect(onSave).toHaveBeenCalledWith(12_500_000, 30, 0);
  });

  it("allows correcting the remaining time without showing a second expense", () => {
    const onSave = vi.fn();
    render(<VipDialog characterName="Sentry1" expiresAt={new Date(Date.now() + 28 * 86_400_000).toISOString()} saving={false} error={null} onClose={vi.fn()} onSave={onSave} />);

    expect(screen.queryByLabelText("Valor pago em gold")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Dias restantes"), { target: { value: "27" } });
    fireEvent.change(screen.getByLabelText("Horas restantes"), { target: { value: "10" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar ajuste" }));

    expect(onSave).toHaveBeenCalledWith(100_000, 27, 10);
  });
});
