import { Link } from 'react-router-dom';
function StatCard({ title, value, buttonText, date, time, onBtnClick}) {
  
  return (
    <div className="stat-card">
      <h3 className="card-title">{title}</h3>
      <h2 className="card-value">{value}</h2>
      
      {/* This logic only shows the button if you provide text for it */}
      {buttonText && (
        <button className="card-action-btn" onClick ={onBtnClick}>
          {buttonText}
        </button>
      )}

      <div className="card-footer">
        <span>{date}</span>
        <span>{time}</span>
      </div>
    </div>
  );
}

export default StatCard