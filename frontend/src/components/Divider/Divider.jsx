const Divider = ({ text = 'or continue with' }) => {
  return (
    <div className="flex items-center w-full gap-0">
      <span className="flex-1 h-px bg-black/10" />
      <span className="px-4 text-sm text-[#45474C] bg-white whitespace-nowrap">
        {text}
      </span>
      <span className="flex-1 h-px bg-black/10" />
    </div>
  );
};

export default Divider;
