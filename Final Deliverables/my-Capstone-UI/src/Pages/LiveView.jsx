{/*import Header from "../components/Header"
import SectionBox from "../components/SectionBox"
import videoImage from '../assets/000033.png'; // Kept as .png!

import { useNavigate } from 'react-router-dom';

function LiveView(){
    const navigate = useNavigate();
    return (
        <div className = 'dashboard-wrapper'>
            <Header></Header>
            <button className="card-action-btn" onClick = {() => navigate('/')}> 
                {"RETURN TO DASHBOARD"}
            </button>
            <SectionBox title = "INTERSECTION LIVE">
                <div className="image-wrapper">
                    <img 
                        src={videoImage} 
                        alt="sample vid" 
                        className="video-image" 
                    />
                </div>
            </SectionBox>
        </div>
    )
}
export default LiveView;*/}

import Header from "../components/Header"
import SectionBox from "../components/SectionBox"
import { useNavigate } from 'react-router-dom';

// 1. Updated the import to point to the new 'live' folder and video name
import liveVideo from '/videos/live/live_simulation.webm'; 

function LiveView(){
    const navigate = useNavigate();
    
    return (
        <div className='dashboard-wrapper'>
            <Header></Header>
            <button className="card-action-btn" onClick={() => navigate('/')}> 
                {"RETURN TO DASHBOARD"}
            </button>
            <SectionBox title="INTERSECTION LIVE">
                <div className="image-wrapper">
                    {/* 2. Video element plays the imported liveVideo */}
                    <video 
                        src={liveVideo} 
                        className="video-image" 
                        controls 
                        autoPlay 
                        loop 
                        muted 
                        style={{ maxWidth: '100%', height: 'auto' }}
                    />
                </div>
            </SectionBox>
        </div>
    )
}

export default LiveView;