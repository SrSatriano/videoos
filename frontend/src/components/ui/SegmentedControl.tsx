interface SegmentedOption<T extends string> {
  label: string;
  value: T;
}

interface SegmentedControlProps<T extends string> {
  value: T;
  options: Array<SegmentedOption<T>>;
  onChange: (value: T) => void;
  label: string;
}

export function SegmentedControl<T extends string>({ value, options, onChange, label }: SegmentedControlProps<T>) {
  return (
    <div className="segmented-field" role="radiogroup" aria-label={label}>
      {options.map((option) => (
        <button
          key={option.value}
          className={option.value === value ? "segmented-button active" : "segmented-button"}
          onClick={() => onChange(option.value)}
          role="radio"
          aria-checked={option.value === value}
          type="button"
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
