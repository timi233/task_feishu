// frontend/src/App.js
import React, { useState, useEffect } from 'react';

function App() {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Fetch tasks from the backend API
    // Use proxy for development, direct URL for production
    const backendUrl = process.env.REACT_APP_BACKEND_URL || '';
    const apiUrl = backendUrl + '/api/tasks';
    
    fetch(apiUrl)
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        // Flatten the data for display
        const allTasks = [];
        Object.keys(data).forEach(day => {
          if (Array.isArray(data[day])) {
            data[day].forEach(task => {
              allTasks.push({ ...task, day });
            });
          }
        });
        setTasks(allTasks);
        setLoading(false);
      })
      .catch(e => {
        console.error('Fetch error:', e);
        setError(e.message);
        setLoading(false);
      });
  }, []);

  if (loading) return <div>Loading tasks...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h1>Task List</h1>
      <p>This frontend connects directly to the backend API.</p>
      <ul>
        {tasks.map((task, index) => (
          <li key={index} style={{ marginBottom: '10px', padding: '10px', border: '1px solid #ccc', borderRadius: '4px' }}>
            <strong>{task.task_name}</strong> - {task.assignee} - {task.status} - {task.day}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default App;