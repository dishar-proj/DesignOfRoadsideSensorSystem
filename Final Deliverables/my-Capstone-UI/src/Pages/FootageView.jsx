{/*import Header from "../components/Header"
import SectionBox from "../components/SectionBox"
import videoImage from '../assets/000056.png'; // Kept as .png!

import carlaData from '../carla_results.json'; 
import { useNavigate } from 'react-router-dom';
import { useState } from "react";

function FootageView(){
    const navigate = useNavigate();
    const [activeImageId, setActiveImageId] = useState(null);

    // Filter for unique speeding vehicles to prevent multiple buttons for the same car
    const uniqueSpeedingVehicles = [];
    const seenIds = new Set();
    
    if (carlaData && carlaData.vehicles) {
        carlaData.vehicles.forEach(v => {
            if (v.is_speeding && !seenIds.has(v.vehicle_id)) {
                seenIds.add(v.vehicle_id);
                uniqueSpeedingVehicles.push(v);
            }
        });
    }

    const handleToggleImage = (vehicleId) => {
        // If clicking the same button, hide the image. Otherwise, show the new one.
        if (activeImageId === vehicleId) {
            setActiveImageId(null);
        } else {
            setActiveImageId(vehicleId);
        }
    };

    return (
        <div className='dashboard-wrapper'>
            <Header></Header>
            <button className="card-action-btn" onClick={() => navigate('/')}> 
                RETURN TO DASHBOARD
            </button>
            
            <SectionBox title="SPEEDING EVENTS">
                <div className="image-wrapper2">
                    {uniqueSpeedingVehicles.length > 0 ? (
                        uniqueSpeedingVehicles.map((vehicle) => (
                            <div key={vehicle.vehicle_id} style={{ marginBottom: '20px', textAlign: 'center' }}>
                                <button 
                                    className="link-button" 
                                    onClick={() => handleToggleImage(vehicle.vehicle_id)}
                                >
                                    Speeding Event: {vehicle.name} ({vehicle.sensor_speed_mps} m/s)
                                </button>

                                {activeImageId === vehicle.vehicle_id && (
                                    <img 
                                        src={videoImage} 
                                        alt={`Speeding event for ${vehicle.name}`}
                                        className="preview-image"
                                        style={{ marginTop: '10px' }}
                                    />
                                )}
                            </div>
                        ))
                    ) : (
                        <p style={{ color: 'white' }}>No speeding events detected.</p>
                    )}
                </div>
            </SectionBox>
        </div>
    )
}

export default FootageView;*/}

import Header from "../components/Header"
import SectionBox from "../components/SectionBox"
import carlaData from '../carla_results.json'; 
import { useNavigate } from 'react-router-dom';

function FootageView(){
    const navigate = useNavigate();

    /* 1. Filter for unique speeding vehicles from your JSON 
    */
    const speedingVehicles = [];
    const seenIds = new Set();
    
    if (carlaData && carlaData.vehicles) {
        carlaData.vehicles.forEach(v => {
            if (v.is_speeding && !seenIds.has(v.vehicle_id)) {
                seenIds.add(v.vehicle_id);
                speedingVehicles.push(v);
            }
        });
    }

    return (
        <div className='dashboard-wrapper'>
            <Header />
            <button className="card-action-btn" onClick={() => navigate('/')}> 
                RETURN TO DASHBOARD
            </button>
            
            <SectionBox title="SPEEDING EVENTS GALLERY">
                {/* 2. This container handles the "Flat Page / Scroll" feel.
                      We use a CSS Grid to show multiple videos at once.
                */}
                <div className="video-grid-container" style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
                    gap: '20px',
                    padding: '20px',
                    maxHeight: '70vh', 
                    overflowY: 'auto' // Adds the scroll wheel if there are many videos
                }}>
                    {speedingVehicles.length > 0 ? (
                        speedingVehicles.map((vehicle) => {
                            // Constructing path: /videos/speeding_events/Name_ID/Name_ID.webm
                            const safeName = vehicle.name.replace(/ /g, "_").replace(/\//g, "_");
                            const folderName = `${safeName}_ID${vehicle.vehicle_id}`;
                            const videoPath = `/videos/speeding_events/${folderName}/${folderName}.webm`;

                            return (
                                <div key={vehicle.vehicle_id} className="video-card" style={{
                                    background: 'rgba(255, 255, 255, 0.1)',
                                    borderRadius: '8px',
                                    padding: '10px',
                                    textAlign: 'center'
                                }}>
                                    <h4 style={{ color: 'white', marginBottom: '10px' }}>
                                        {vehicle.name} (ID: {vehicle.vehicle_id})
                                    </h4>
                                    
                                    <video 
                                        src={videoPath} 
                                        controls 
                                        muted 
                                        loop
                                        style={{ width: '100%', borderRadius: '4px' }}
                                    />
                                    
                                    <p style={{ color: '#ff4d4d', fontWeight: 'bold', marginTop: '5px' }}>
                                        Speed: {vehicle.sensor_speed_mps} m/s
                                    </p>
                                </div>
                            );
                        })
                    ) : (
                        <p style={{ color: 'white' }}>No speeding event footage found.</p>
                    )}
                </div>
            </SectionBox>
        </div>
    )
}

export default FootageView;