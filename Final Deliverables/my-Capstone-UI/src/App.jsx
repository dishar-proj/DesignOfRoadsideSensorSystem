import './index.css';
import {HashRouter as Router, Routes, Route} from 'react-router-dom';
import DashHomes from './Pages/MainDashboard'
import LiveView from './Pages/LiveView'
import FootageView from './Pages/FootageView';

function App() {
  return (
    <Router>
      <Routes>
        <Route path ="/" element={<DashHomes/>}/>
        <Route path ="/liveView" element={<LiveView/>}/>
        <Route path ="/footageView" element={<FootageView/>}/>
      </Routes>
    </Router> 
  )
}

export default App
