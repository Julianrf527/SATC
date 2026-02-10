type Props = { title?: string; body ?: string; };

function TitleForm({ title, body }: Props) {
  return (
    <>
      <div className="mb-6 text-center">
          <h2 className="text-3xl font-bold mb-2">{title}</h2>
          <p className="text-sm text-gray-500">{body}</p>
      </div>
    </>
  );
}

export default TitleForm;
