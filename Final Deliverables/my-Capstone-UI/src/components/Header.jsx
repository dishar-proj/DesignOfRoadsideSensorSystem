import dashboardImg from '../assets/RowenLogo.jpg';

function Header(){

    return(
      <div className="image-wrapper">
        <img 
          src={dashboardImg} 
          alt="Smart Intersection Visualization" 
          className="main-dashboard-image" 
        />
      </div>
    );
}

export default Header