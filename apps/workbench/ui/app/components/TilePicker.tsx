"use client";

export interface Tile {
  value: string;
  label: string;
  description?: string;
}

interface TilePickerProps {
  tiles: Tile[];
  selected: string | string[] | null;
  onSelect: (value: string) => void;
  columns?: 2 | 3 | 4;
}

/**
 * A row of clickable tiles standing in for a <select>/radio-group, styled so
 * an operator with no domain knowledge can just click through what is
 * available rather than typing a value they'd have to already know. Single-
 * vs multi-select is entirely up to the caller (a plain value vs an array
 * for `selected`, and what `onSelect` does with a click) -- each tile's own
 * `aria-pressed` already conveys "toggled or not" regardless of which mode
 * the caller is using, so there is no group-level ARIA role this needs.
 */
export function TilePicker({
  tiles,
  selected,
  onSelect,
  columns = 3,
}: TilePickerProps) {
  const isSelected = (value: string) =>
    Array.isArray(selected) ? selected.includes(value) : selected === value;

  const gridCols =
    columns === 2
      ? "grid-cols-2"
      : columns === 4
        ? "grid-cols-4"
        : "grid-cols-3";

  return (
    <div className={`grid ${gridCols} gap-2`}>
      {tiles.map((tile) => {
        const active = isSelected(tile.value);
        return (
          <button
            key={tile.value}
            type="button"
            onClick={() => onSelect(tile.value)}
            aria-pressed={active}
            className={`text-left rounded-lg border px-3 py-2 text-sm transition-colors ${
              active
                ? "border-blue-600 bg-blue-50 text-blue-900 ring-1 ring-blue-600"
                : "border-gray-300 bg-white hover:border-gray-400 hover:bg-gray-50"
            }`}
          >
            <div className="font-medium">{tile.label}</div>
            {tile.description && (
              <div className="text-xs text-gray-500 mt-0.5">
                {tile.description}
              </div>
            )}
          </button>
        );
      })}
    </div>
  );
}
