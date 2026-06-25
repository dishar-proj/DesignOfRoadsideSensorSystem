import { useState, useEffect } from 'react';
import Header from '../components/Header.jsx';
import StatCard from '../components/StatCard.jsx';
import '../index.css';
import { useNavigate } from 'react-router-dom';

// Import the JSON directly
import carlaData from '../carla_results.json';

function DashHomes() {
  const navigate = useNavigate();
  
  // Calculate dynamic stats directly from the JSON summary and vehicle arrays
  let totalVehicles = 0;
  let speedingCount = 0;

  if (carlaData && carlaData.vehicles) {
     const uniqueVehicleIds = new Set(carlaData.vehicles.map(v => v.vehicle_id));
     totalVehicles = uniqueVehicleIds.size;

     const uniqueSpeedingIds = new Set(
         carlaData.vehicles.filter(v => v.is_speeding).map(v => v.vehicle_id)
     );
     speedingCount = uniqueSpeedingIds.size;
  }
  
  const totalPedestrians = carlaData?.summary?.total_pedestrians || 0; 
  
  const [stats, setStats] = useState({
    totalTraffic: totalVehicles + totalPedestrians,
    vehiclesAtIntersection: totalVehicles,
    pedestriansAtIntersection: totalPedestrians,
    speedingEvents: speedingCount
  });

  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 60000);
    return () => clearInterval(timer); 
  }, []);

  const dateString = currentTime.toLocaleDateString('en-US', { 
    month: '2-digit', day: '2-digit', year: 'numeric' 
  });
  const timeString = currentTime.toLocaleTimeString('en-US', { 
    hour: '2-digit', minute: '2-digit', hour12: true 
  }).toLowerCase();

  return (
    <div className="dashboard-wrapper">
      <Header />
 
      <main className="cards-container">
          <StatCard 
            title="TOTAL INTERSECTION TRAFFIC" 
            value={stats.totalTraffic} 
            date={dateString} 
            time={timeString} 
          />
          <StatCard 
            title="VEHICLES AT INTERSECTION" 
            value={stats.vehiclesAtIntersection} 
            buttonText="VIEW LIVE"
            onBtnClick={() => navigate('/liveView')}
            date={dateString} 
            time={timeString} 
          />
           <StatCard 
            title="PEDESTRIANS AT INTERSECTION" 
            value={stats.pedestriansAtIntersection} 
            date={dateString} 
            time={timeString} 
          />
          <StatCard 
            title="SPEEDING EVENTS" 
            value={stats.speedingEvents} 
            buttonText="VIEW FOOTAGE"
            onBtnClick={() => navigate('/footageView')}
            date={dateString} 
            time={timeString} 
          />
        </main>
    </div>
  );
}

export default DashHomes;