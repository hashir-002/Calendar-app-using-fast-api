import React, {useState, useEffect} from 'react';
import axios from "axios";
import jwt_decode from "jwt-decode";
import Calendar from "react-big-calendar";
import moment from "moment";
import "react-big-calendar/lib/css/react-big-calendar.css";
import './App.css';

const localizer = Calendar.momentLocalizer(moment);

function App() {

  //state to manage events
  const [events, setEvents] = useState([]);
  const [title, setTitle] = useState([""]);
  const [description, setDescription] = useState([""]);
  const [startTime, setStartTime] = useState([""]);
  const [endTime, setEndTime] = useState([""]);
  const [userDefined, setUserDefined] = useState([false]);

  // state for authentication 
  const [token, setToken] = useState("");
  const [role, setRole] = useState("")

  //state for loginforms
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")

  // load events when token is available
  useEffect(() => {
    const tokenFromStorage = localStorage.getItem("token");
    if (tokenFromStorage) {
      const decoded = jwt_decode(tokenFromStorage);
      setToken(tokenFromStorage);
      setRole(decoded.role);
      fetchEvents(tokenFromStorage);
    }
  }, []);

  //fetch events for the logged in user

  const fetchEvents = async (authToken) => {
    try {
      const response = await axios.get("http://localhost:8000/events/", {
        headers : {Authorization: `Bearer ${authToken}`}
      });
      const eventList = response.data.map((event) => ({
        title : event.title,
        start : new Date(event.start_time), 
        end : new Date(event.end_time),
      }));
      setEvents(eventList);
    } catch(error) {
      console.error("Error fetching events:", error);
      
    }
  };


  //handle login form submission
  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post("http://localhost:8000/token", {
        username,
        password,
      });
      const decoded = jwt_decode(response.data.access_token);
      setToken(response.data.access_token);
      setRole(decoded.role);
      localStorage.setItem("token", response.data.access_token);
      fetchEvents(response.data.access_token);
    } catch(error) {
      console.error("Login Failed: ", error);
    }
  };

  //handle event creation form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    const newEvent = {
      title,
      description,
      start_time: startTime,
      end_time: endTime,
      user_defined : userDefined,
    };
    try {
      await axios.post("http://localhost:8000/events/", newEvent, {
        headers: {Authorization: `Bearer ${token}`},
      });
      setEvents([
        ...events,{...newEvent, start: new Date(startTime), end: new Date(endTime)},
      ]);
    } catch(error) {
      console.error("error creating event: ", error)
    }
  };






  return (
    <div>
      <h1>Calendar App</h1>
        { !token ? (
           <form onSubmit={handleLogin}>
            <input type='text' placeholder='Username' value={username} onChange={(e) => setUsername(e.target.value)} required/>
            <input type='password' placeholder='Password' value={password} onChange={(e) => setPassword(e.target.value)} required/>
            <button type='submit'>Login</button>
           </form>
        ) : (
          <div>
            {/* Event creation form */}
            <form onSubmit={handleSubmit}>
              <input type='text' placeholder='Event Title' value={title} onChange={(e) => setTitle(e.target.value)} required />
              <input type='text' placeholder='Event Description' value={description} onChange={(e) => setDescription(e.target.value)} required />
              <input type='datetime-local'  value={startTime} onChange={(e) => setStartTime(e.target.value)} required />
              <input type='datetime-local'  value={endTime} onChange={(e) => setEndTime(e.target.value)} required />
              <label>
                <input type='chechbox' checked={userDefined} onChange={(e)=> setUserDefined(e.target.checked)} />
                User Defined
              </label>
              <button type='submit'>Create Event</button>
            </form>

            <Calendar localizer = {localizer} events = {events} startAccessor = "start" endAccessor = "end" style = {{height: 500}} />
          </div>
          
          
        ) 
      }
      
      
    </div>
  );
}

export default App;
