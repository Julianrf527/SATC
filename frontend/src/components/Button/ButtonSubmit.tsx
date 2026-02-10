
type Props = { text?: string};

function ButtonUser({ text }: Props) {
  return (
    <button
        type="submit"
        className="w-full bg-green-600 text-white py-2 rounded-md hover:bg-green-700 transition duration-300"
      >
        {text}
    </button>
  );
}

export default ButtonUser;
