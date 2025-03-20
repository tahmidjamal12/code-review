import React, { useState, useEffect } from 'react';

const Chat = ({ selectedJob }) => {
  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001';

  const [messages, setMessages] = useState([
    {
      id: 1,
      role: 'assistant',
      text: 'Hi! I am an assistant that can answer any question you have about this process map. Please double check important details, as I can make mistakes.'
    }
  ]);
  const [newMessage, setNewMessage] = useState('');
  const [isChatHidden, setIsChatHidden] = useState(false);

  // Toggle chat visibility and update main content padding
  const toggleChat = () => {
    setIsChatHidden(!isChatHidden);
    
    // Update main content class for proper padding
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
      if (!isChatHidden) {
        mainContent.classList.add('chat-hidden');
      } else {
        mainContent.classList.remove('chat-hidden');
      }
    }
  };

  // Initialize main content padding based on chat visibility on mount
  useEffect(() => {
    const mainContent = document.querySelector('.main-content');
    if (mainContent && isChatHidden) {
      mainContent.classList.add('chat-hidden');
    }
    
    // Clean up when component unmounts
    return () => {
      if (mainContent) {
        mainContent.classList.remove('chat-hidden');
      }
    };
  }, []);

  const handleSendMessage = (e) => {
    e.preventDefault();
    
    // Ignore if user message is empty
    if (!newMessage.trim()) {
      return;
    }

    // Ignore if no job is selected
    if (!selectedJob) {
      alert('Please select a process job first to ask questions about it.');
      return;
    }

    // Add user message
    const userMessage = {
      id: messages.length + 1,
      role: 'user',
      text: newMessage
    };
    
    setMessages([...messages, userMessage]);
    setNewMessage('');
    
    // Send request to server
    fetch(`${API_URL}/chat_response`, {
      method: 'POST',
      body: JSON.stringify({ 
        conversation: [...messages, userMessage],
        runId: selectedJob?.runId,
       }),
      headers: {
        'Content-Type': 'application/json'
      }
    })
    .then(response => response.json())
    .then(data => {
      console.log('Received response from server:', data);
      if (data.error) {
        // Received error from server
        // TODO -- replace alert with a toast notification
        alert(data.error);
        return;
      } else {
        // Received valid response from server, add to messages
        const assistantMessage = {
          id: messages.length + 2,
          role: 'assistant',
          text: data.text
        };
      
        setMessages(prevMessages => [...prevMessages, assistantMessage]);
      }
    })
    .catch(error => {
      alert('Error: ' + error);
      console.error('Error:', error);
    });
  };

  // Simple response generator based on the user's message and selected job data
  const generateResponse = (message, job) => {
    if (!job) {
      return "Please select a process job first to ask questions about it.";
    }
    
    const lowerMessage = message.toLowerCase();
    
    if (lowerMessage.includes('bottleneck') || lowerMessage.includes('issue') || lowerMessage.includes('problem')) {
      return job.bottlenecks 
        ? `Here are the bottlenecks identified in this process: ${job.bottlenecks.slice(0, 150)}...` 
        : "I'm still analyzing bottlenecks for this process. Please check back soon.";
    }
    
    if (lowerMessage.includes('improve') || lowerMessage.includes('suggestion') || lowerMessage.includes('better')) {
      return job.improvements 
        ? `Here are some improvement suggestions: ${job.improvements.slice(0, 150)}...` 
        : "I'm still generating improvement suggestions for this process. Please check back soon.";
    }
    
    if (lowerMessage.includes('process') || lowerMessage.includes('map') || lowerMessage.includes('overview')) {
      return job.processMap 
        ? `Here's a summary of the process map: ${job.processMap.slice(0, 150)}...` 
        : "I'm still analyzing the process map. Please check back soon.";
    }
    
    if (lowerMessage.includes('status') || lowerMessage.includes('progress')) {
      const progress = job.processMap ? (job.bottlenecks ? (job.improvements ? 100 : 66) : 33) : 15;
      return `The current analysis is about ${progress}% complete.`;
    }
    
    return "I can answer questions about the process map, bottlenecks, and improvement suggestions. What would you like to know?";
  };

  return (
    <div className={`chat-sidebar ${isChatHidden ? 'hidden' : ''}`}>
      <div className="chat-toggle-tab" onClick={toggleChat}></div>
      <div className="chat-header">
        <h2>Chat</h2>
      </div>
      
      <div className="chat-messages">
        {messages.map(message => (
          <div key={message.id} className={`message ${message.role}`}>
            <div className="message-content">
              {message.text}
            </div>
          </div>
        ))}
      </div>
      
      <form className="chat-form" onSubmit={handleSendMessage}>
        <input
          type="text"
          placeholder="Type your message..."
          value={newMessage}
          onChange={(e) => setNewMessage(e.target.value)}
          className="chat-input"
        />
        <button type="submit" className="chat-button">
          Send
        </button>
      </form>
    </div>
  );
};

export default Chat;
