type Props = {
  title?: string;
  type?: string;
  required?: boolean;
  placeholder?: string;
  minLength?: number;
  maxLength?: number;
  value?: string | number;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onKeyUp?: (e: React.KeyboardEvent<HTMLInputElement>) => void;
  inputRef?: React.RefObject<HTMLInputElement | null>;
};

export default function Input({
  title,
  type,
  required,
  placeholder,
  minLength,
  maxLength,
  value,
  onChange,
  onKeyUp,
  inputRef,
}: Props) {
  // Determinar si es un input controlado o no controlado
  const isControlled = value !== undefined;

  return (
    <div>
      {title && (
        <label className="block mb-2 text-sm font-medium">{title}</label>
      )}
      <input
        required={required ?? true}
        placeholder={placeholder}
        type={type ?? "text"}
        ref={inputRef}
        onKeyUp={onKeyUp}
        minLength={minLength}
        maxLength={maxLength}
        className="input input-bordered w-full"
        // Props condicionales para controlado vs no controlado
        {...(isControlled ? { value, onChange } : { defaultValue: value })}
      />
    </div>
  );
}
