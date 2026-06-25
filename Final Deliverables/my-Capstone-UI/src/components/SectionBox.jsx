function SectionBox({ title, children }) {
    return (
    <div className="white-box">
      <h2 className="white-box-title">{title}</h2>
      <div className="white-box-content">
        {children}
      </div>
    </div>
  );
}

export default SectionBox;
