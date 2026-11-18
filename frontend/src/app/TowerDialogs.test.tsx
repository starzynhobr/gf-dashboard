import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { TowerConfiguration, TowerConfigurationInput, TowerRegistrationInput } from "../gateway/AppGateway";
import { TowerConfigurationDialog } from "./TowerConfigurationDialog";
import { TowerDialog } from "./TowerDialog";

const configuration: TowerConfiguration = {
  guildName: "Guardiões",
  entryCostGold: 35_000,
  participantIds: ["character-1"],
  items: [{ itemId: "item-1", itemName: "Drop raro", estimatedUnitValue: 120_000 }],
};
const characters = [{ id: "character-1", name: "Star01", className: "Ranger", accountName: "Conta", completedDungeons: 0, selectedDungeons: 9 }];

function savedConfiguration(input: TowerConfigurationInput): TowerConfiguration {
  return { ...input, items: input.items.map((item, index) => ({ ...item, itemId: `item-${index}` })) };
}

function renderConfiguration(onSave = vi.fn(async (input: TowerConfigurationInput) => savedConfiguration(input))) {
  const onClose = vi.fn();
  const onRegister = vi.fn();
  render(<TowerConfigurationDialog configuration={configuration} characters={characters} loading={false} error={null} onRetry={vi.fn()} onClose={onClose} onSave={onSave} onRegister={onRegister} />);
  return { onSave, onClose, onRegister };
}

afterEach(cleanup);

describe("TowerConfigurationDialog", () => {
  it.each(["", "-1", "1.5", "9007199254740992", "Infinity", "1e3"])("rejects invalid opening cost %j before calling the gateway", async (value) => {
    const { onSave } = renderConfiguration();

    fireEvent.change(screen.getByLabelText("Custo da abertura (gold)"), { target: { value } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar configuração" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/Custo da abertura/);
    expect(onSave).not.toHaveBeenCalled();
  });

  it.each(["-1", "1.5", "9007199254740992"])("rejects invalid item estimate %j before calling the gateway", async (value) => {
    const { onSave } = renderConfiguration();

    fireEvent.change(screen.getByLabelText("Valor estimado do item 1 (gold)"), { target: { value } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar configuração" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/Valor de Drop raro/);
    expect(onSave).not.toHaveBeenCalled();
  });

  it("accepts zero cost and an absent item estimate without converting it to zero", async () => {
    const { onSave } = renderConfiguration();

    fireEvent.change(screen.getByLabelText("Custo da abertura (gold)"), { target: { value: "0" } });
    fireEvent.change(screen.getByLabelText("Valor estimado do item 1 (gold)"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar configuração" }));

    expect(await screen.findByText("Configuração salva.")).toBeInTheDocument();
    expect(onSave).toHaveBeenCalledWith({ guildName: "Guardiões", entryCostGold: 0, participantIds: ["character-1"], items: [{ itemName: "Drop raro", estimatedUnitValue: null }], idempotencyKey: expect.any(String) });
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("requires a name for every catalog row and blocks duplicate names", async () => {
    const { onSave } = renderConfiguration();
    fireEvent.click(screen.getByRole("button", { name: "Adicionar item" }));
    fireEvent.click(screen.getByRole("button", { name: "Salvar configuração" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/nome de todos os itens/);

    fireEvent.change(screen.getByLabelText("Nome do item 2"), { target: { value: " drop RARO " } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar configuração" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/não podem se repetir/);
    expect(onSave).not.toHaveBeenCalled();
  });

  it("removes a catalog item only on save and blocks session registration while changes are unsaved", async () => {
    const { onSave, onRegister } = renderConfiguration();
    fireEvent.click(screen.getByRole("button", { name: "Remover item 1" }));
    expect(screen.queryByLabelText("Nome do item 1")).not.toBeInTheDocument();
    expect(onSave).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Registrar sessão" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Registrar sessão" }));
    expect(onRegister).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Salvar configuração" }));
    await screen.findByText("Configuração salva.");
    expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ items: [] }));
    fireEvent.click(screen.getByRole("button", { name: "Registrar sessão" }));
    expect(onRegister).toHaveBeenCalledOnce();
  });

  it("keeps edits after a failed save and retries the same intent with the same idempotency key", async () => {
    const onSave = vi.fn<(input: TowerConfigurationInput) => Promise<TowerConfiguration>>()
      .mockRejectedValueOnce(new Error("Falha ao salvar"))
      .mockImplementation(async (input) => savedConfiguration(input));
    renderConfiguration(onSave);
    fireEvent.change(screen.getByLabelText("Guilda"), { target: { value: "Guilda alterada" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar configuração" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Falha ao salvar");
    expect(screen.getByLabelText("Guilda")).toHaveValue("Guilda alterada");

    fireEvent.click(screen.getByRole("button", { name: "Salvar configuração" }));

    await screen.findByText("Configuração salva.");
    expect(onSave).toHaveBeenCalledTimes(2);
    expect(onSave.mock.calls[1][0]).toEqual(onSave.mock.calls[0][0]);
  });

  it("prevents a second save while the first request is pending", async () => {
    let completeSave!: (result: TowerConfiguration) => void;
    const onSave = vi.fn<(input: TowerConfigurationInput) => Promise<TowerConfiguration>>(() => new Promise<TowerConfiguration>((resolve) => { completeSave = resolve; }));
    renderConfiguration(onSave);

    fireEvent.click(screen.getByRole("button", { name: "Salvar configuração" }));
    const saving = screen.getByRole("button", { name: "Salvando..." });
    expect(saving).toBeDisabled();
    expect(screen.getByLabelText("Guilda")).toBeDisabled();
    fireEvent.click(saving);
    expect(onSave).toHaveBeenCalledTimes(1);

    await act(async () => completeSave(configuration));
    expect(await screen.findByText("Configuração salva.")).toBeInTheDocument();
  });
});

describe("TowerDialog", () => {
  it("does not turn a configured item into a drop until a positive quantity is entered", async () => {
    const onSave = vi.fn(async () => {});
    render(<TowerDialog configuration={configuration} activityDate="2026-08-26" characters={characters} saving={false} error={null} onClose={vi.fn()} onSave={onSave} />);
    expect(screen.getByRole("checkbox", { name: /Star01/ })).toBeChecked();
    expect(screen.getByLabelText("Quantidade de Drop raro")).toHaveValue("0");

    fireEvent.click(screen.getByRole("button", { name: "Confirmar sessão" }));

    await waitFor(() => expect(onSave).toHaveBeenCalledWith({ guildName: "Guardiões", activityDate: "2026-08-26", participantIds: ["character-1"], drops: [], idempotencyKey: expect.any(String) }));
  });

  it.each(["", "-1", "1.5", "9007199254740992"])("rejects invalid drop quantity %j instead of coercing it", async (value) => {
    const onSave = vi.fn(async () => {});
    render(<TowerDialog configuration={configuration} activityDate="2026-08-26" characters={characters} saving={false} error={null} onClose={vi.fn()} onSave={onSave} />);
    fireEvent.change(screen.getByLabelText("Quantidade de Drop raro"), { target: { value } });

    fireEvent.click(screen.getByRole("button", { name: "Confirmar sessão" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/Quantidade/);
    expect(onSave).not.toHaveBeenCalled();
  });

  it("retries the same session date and idempotency key when the Home date changes", async () => {
    const onSave = vi.fn<(input: TowerRegistrationInput) => Promise<void>>()
      .mockRejectedValueOnce(new Error("Falha de conexão"))
      .mockResolvedValue(undefined);
    const onClose = vi.fn();
    const view = render(<TowerDialog configuration={configuration} activityDate="2026-08-26" characters={characters} saving={false} error={null} onClose={onClose} onSave={onSave} />);
    fireEvent.change(screen.getByLabelText("Quantidade de Drop raro"), { target: { value: "2" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirmar sessão" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Falha de conexão");

    view.rerender(<TowerDialog configuration={configuration} activityDate="2026-08-27" characters={characters} saving={false} error={null} onClose={onClose} onSave={onSave} />);
    fireEvent.click(screen.getByRole("button", { name: "Confirmar sessão" }));

    await waitFor(() => expect(onSave).toHaveBeenCalledTimes(2));
    expect(onSave.mock.calls[0][0]).toMatchObject({ activityDate: "2026-08-26", drops: [{ itemName: "Drop raro", quantity: 2, estimatedUnitValue: 120_000 }] });
    expect(onSave.mock.calls[1][0]).toEqual(onSave.mock.calls[0][0]);
  });
});
