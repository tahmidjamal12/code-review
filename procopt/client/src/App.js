import React, { useState, useEffect } from 'react';
import Chat from './Chat';

function App() {
  // Add API base URL
  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001';
  
  // State for managing multiple jobs
  const [jobs, setJobs] = useState([]);
  const [selectedJobId, setSelectedJobId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');

  // Get the selected job from the jobs array
  const selectedJob = jobs.find(job => job.runId === selectedJobId) || null;

  // Progress status messages
  const progressMessages = {
    transcription: {
      pending: "Waiting to start...",
      processing: "Analyzing process map...",
      complete: "Process map analyzed"
    },
    bottlenecks: {
      pending: "Waiting for process map...",
      processing: "Identifying bottlenecks...",
      complete: "Bottlenecks identified"
    },
    improvements: {
      pending: "Waiting for bottlenecks...",
      processing: "Generating improvement suggestions...",
      complete: "Improvements generated"
    }
  };

  // Calculate overall progress percentage for a job
  const calculateProgress = (job) => {
    if (!job) return 0;
    
    let progress = 0;
    
    // Process map transcription (33%)
    if (job.processMap) {
      progress += 33;
    } else {
      // Always show some progress for the first step since it starts immediately
      progress += 15;
    }
    
    // Bottlenecks identification (33%)
    if (job.bottlenecks) {
      progress += 33;
    } else if (job.bottlenecksRequested) {
      progress += 15;
    }
    
    // Improvements suggestions (34%)
    if (job.improvements) {
      progress += 34;
    } else if (job.improvementsRequested) {
      progress += 15;
    }
    
    return progress;
  };

  // Get status message for a specific step
  const getStepStatus = (job, step) => {
    if (!job) return progressMessages[step].pending;
    
    switch(step) {
      case 'transcription':
        // Always show as processing when a file is uploaded since transcription starts immediately
        if (job.processMap) return progressMessages.transcription.complete;
        // Always show processing for transcription since it starts immediately after upload
        return progressMessages.transcription.processing;
      
      case 'bottlenecks':
        if (job.bottlenecks) return progressMessages.bottlenecks.complete;
        return job.bottlenecksRequested ? progressMessages.bottlenecks.processing : progressMessages.bottlenecks.pending;
      
      case 'improvements':
        if (job.improvements) return progressMessages.improvements.complete;
        return job.improvementsRequested ? progressMessages.improvements.processing : progressMessages.improvements.pending;
      
      default:
        return "Unknown step";
    }
  };

  // Polling effect for all jobs
  useEffect(() => {
    if (jobs.length === 0) return;

    const interval = setInterval(async () => {
      // Create a copy of jobs to update
      const updatedJobs = [...jobs];
      let hasUpdates = false;

      // Check each job that's not complete
      for (let i = 0; i < updatedJobs.length; i++) {
        const job = updatedJobs[i];
        
        // Skip jobs that are already complete
        if (job.status === 'complete' || job.status?.includes('failed')) continue;

        try {
          const response = await fetch(`${API_URL}/runs/${job.runId}`);
          const data = await response.json();
          
          // Update job data
          if (data.status !== job.status || 
              data.transcription !== job.processMap ||
              data.bottlenecks !== job.bottlenecks ||
              data.improvements !== job.improvements) {
            
            // Calculate the current step based on available data
            let newCurrentStep = job.currentStep;
            if (data.transcription) newCurrentStep = Math.max(newCurrentStep, 2);
            if (data.bottlenecks) newCurrentStep = Math.max(newCurrentStep, 3);
            if (data.improvements) newCurrentStep = Math.max(newCurrentStep, 4);
            
            updatedJobs[i] = {
              ...job,
              status: data.status,
              processMap: data.transcription || job.processMap,
              bottlenecks: data.bottlenecks || job.bottlenecks,
              improvements: data.improvements || job.improvements,
              currentStep: newCurrentStep,
              // Keep transcriptionInProgress true until we get the transcription
              transcriptionInProgress: data.transcription ? false : true
            };
            hasUpdates = true;
            
            // Automatically trigger the next step if needed
            if (data.transcription && !data.bottlenecks && !job.bottlenecksRequested) {
              // Mark this job as having bottlenecks requested to prevent multiple requests
              updatedJobs[i].bottlenecksRequested = true;
              // Queue the bottlenecks identification (will run after the state update)
              setTimeout(() => identifyBottlenecks(job.runId), 1000);
            }
            
            if (data.bottlenecks && !data.improvements && !job.improvementsRequested) {
              // Mark this job as having improvements requested to prevent multiple requests
              updatedJobs[i].improvementsRequested = true;
              // Queue the improvements suggestion (will run after the state update)
              setTimeout(() => suggestImprovements(job.runId), 1000);
            }
          }
        } catch (error) {
          console.error(`Error polling for updates for job ${job.runId}:`, error);
        }
      }

      // Only update state if there were changes
      if (hasUpdates) {
        setJobs(updatedJobs);
      }
    }, 2000); // Poll every 2 seconds

    // Cleanup function to clear interval when component unmounts
    return () => clearInterval(interval);
  }, [jobs, API_URL]);

  const handleFileUpload = async (event) => {
    const uploadedFiles = event.target.files;
    if (uploadedFiles.length === 0) return;

    // Process each file
    for (let i = 0; i < uploadedFiles.length; i++) {
      const file = uploadedFiles[i];
      await processFile(file);
    }
  };

  const handleDragOver = (event) => {
    event.preventDefault();
  };

  const handleDrop = async (event) => {
    event.preventDefault();
    const droppedFiles = event.dataTransfer.files;
    if (droppedFiles.length === 0) return;

    // Process each file
    for (let i = 0; i < droppedFiles.length; i++) {
      const file = droppedFiles[i];
      await processFile(file);
    }
  };

  const processFile = async (file) => {
    setLoading(true);
    setUploadStatus(`Uploading ${file.name}...`);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_URL}/upload`, {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Upload response:', data);
      
      if (data.run_id) {
        // Create a new job and add it to the jobs array
        const newJob = {
          runId: data.run_id,
          fileName: file.name,
          status: 'processing',
          processMap: '',
          bottlenecks: '',
          improvements: '',
          currentStep: 1,
          uploadTime: new Date().toLocaleString(),
          bottlenecksRequested: false,
          improvementsRequested: false,
          transcriptionInProgress: true // Mark transcription as in progress when file is uploaded
        };
        
        setJobs(prevJobs => [...prevJobs, newJob]);
        
        // Select the new job if no job is selected
        if (!selectedJobId) {
          setSelectedJobId(newJob.runId);
        }
        console.log('New job created:', newJob);
        
        setUploadStatus(`${file.name} uploaded successfully!`);
        setTimeout(() => setUploadStatus(''), 3000);
      } else {
        throw new Error('No run_id received from server');
      }
    } catch (error) {
      console.error('Error uploading file:', error);
      setUploadStatus(`Upload failed for ${file.name}: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const identifyBottlenecks = async (runId) => {
    if (!runId) return;
    
    // Find the job and mark it as having bottlenecks requested
    setJobs(prevJobs => 
      prevJobs.map(job => 
        job.id === runId 
          ? { ...job, bottlenecksRequested: true } 
          : job
      )
    );
    
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/runs/${runId}/process/bottlenecks`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      console.log('Bottlenecks response:', data);
    } catch (error) {
      console.error('Error identifying bottlenecks:', error);
      alert('Error identifying bottlenecks: ' + error.message);
      
      // Reset the requested flag on error
      setJobs(prevJobs => 
        prevJobs.map(job => 
          job.runId === runId 
            ? { ...job, bottlenecksRequested: false } 
            : job
        )
      );
    } finally {
      setLoading(false);
    }
  };

  const suggestImprovements = async (runId) => {
    if (!runId) return;
    
    // Find the job and mark it as having improvements requested
    setJobs(prevJobs => 
      prevJobs.map(job => 
        job.runId === runId 
          ? { ...job, improvementsRequested: true } 
          : job
      )
    );
    
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/runs/${runId}/process/improvements`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      console.log('Improvements response:', data);
    } catch (error) {
      console.error('Error suggesting improvements:', error);
      alert('Error suggesting improvements: ' + error.message);
      
      // Reset the requested flag on error
      setJobs(prevJobs => 
        prevJobs.map(job => 
          job.runId === runId 
            ? { ...job, improvementsRequested: false } 
            : job
        )
      );
    } finally {
      setLoading(false);
    }
  };

  const downloadAsMd = async (runId, type) => {
    if (!runId) return;
    
    try {
      const response = await fetch(`${API_URL}/runs/${runId}/export/${type}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      console.log('Download response:', data);
      
      const element = document.createElement('a');
      const file = new Blob([data.content], {type: 'text/markdown'});
      element.href = URL.createObjectURL(file);
      element.download = data.filename;
      document.body.appendChild(element);
      element.click();
      document.body.removeChild(element);
    } catch (error) {
      console.error('Error downloading file:', error);
      alert('Error downloading file: ' + error.message);
    }
  };

  const removeJob = (runId) => {
    setJobs(prevJobs => prevJobs.filter(job => job.runId !== runId));
    
    // If the removed job was selected, select another job or set to null
    if (selectedJobId === runId) {
      const remainingJobs = jobs.filter(job => job.runId !== runId);
      setSelectedJobId(remainingJobs.length > 0 ? remainingJobs[0].runId : null);
    }
  };

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>I<span className="ai-text">AI</span>S Tool</h1>
      </header>
      
      <div className="dashboard-content">
        <aside className="sidebar">
          <div className="sidebar-header">
            <h2>Processes</h2>
            <div className="upload-container">
              <input
                type="file"
                accept="image/*,.pdf"
                onChange={handleFileUpload}
                id="file-upload"
                multiple
              />
              <label htmlFor="file-upload" className="upload-button">
                + New Process Map
              </label>
            </div>
          </div>
          
          <div className="jobs-list">
            {jobs.length === 0 ? (
              <div className="no-jobs">
                <p>Upload a process map to get started</p>
              </div>
            ) : (
              jobs.map(job => (
                <div 
                  key={job.runId} 
                  className={`job-item ${selectedJobId === job.runId ? 'selected' : ''}`}
                  onClick={() => setSelectedJobId(job.runId)}
                >
                  <div className="job-info">
                    <div className="job-name">{job.fileName}</div>
                    <div className="job-status">
                      {job.status === 'complete' ? (
                        <>
                          <span className="status-indicator complete"></span>
                          Complete
                        </>
                      ) : (
                        <>
                          <span className="status-indicator processing"></span>
                          <span className="spinner-small"></span>
                          Processing
                        </>
                      )}
                    </div>
                    <div className="job-progress">
                      <div className="progress-bar">
                        <div 
                          className="progress-fill" 
                          style={{ width: `${calculateProgress(job)}%` }}
                        ></div>
                      </div>
                      <div className="progress-percentage">{calculateProgress(job)}%</div>
                    </div>
                    <div className="job-time">{job.uploadTime}</div>
                  </div>
                  <button 
                    className="remove-job" 
                    onClick={(e) => {
                      e.stopPropagation();
                      removeJob(job.runId);
                    }}
                  >
                    ×
                  </button>
                </div>
              ))
            )}
          </div>
        </aside>
        
        <main className="main-content">
          {!selectedJob ? (
            <div className="upload-area-container">
              <div 
                className="upload-area"
                onDragOver={handleDragOver}
                onDrop={handleDrop}
              >
                <div className="upload-content">
                  <h3>Upload Process Map</h3>
                  <p>Drag and drop files here</p>
                  <p className="file-types">Limit 20MB per file (PDF, PNG, JPG, and JPEG)</p>
                  <input
                    type="file"
                    accept="image/*,.pdf"
                    onChange={handleFileUpload}
                    id="main-file-upload"
                    multiple
                  />
                  <label htmlFor="main-file-upload" className="browse-button">
                    Browse files
                  </label>
                </div>
                {uploadStatus && <div className="upload-status">{uploadStatus}</div>}
                {loading && <div className="loading">Processing...</div>}
              </div>
              
              <section className="instructions">
                <h2>Instructions</h2>
                <p>To start, please upload an image or PDF of your process map. It can be a screenshot of a process map from a tool like Visio, Lucidchart, etc., a photo of a hand-drawn sketch, or any other visual representation of a process.</p>
                <p>You can upload multiple process maps and they will be processed simultaneously.</p>
              </section>
            </div>
          ) : (
            <div className="job-details">
              <div className="job-header">
                <h2>{selectedJob.fileName}</h2>
                <div className="job-actions">
                  <button 
                    className="action-button"
                    onClick={() => removeJob(selectedJob.runId)}
                  >
                    Remove Job
                  </button>
                </div>
              </div>
              
              <div className="job-progress-overview">
                <h3>Overall Progress</h3>
                <div className="progress-bar-large">
                  <div 
                    className="progress-fill" 
                    style={{ width: `${calculateProgress(selectedJob)}%` }}
                  ></div>
                </div>
                <div className="progress-steps">
                  <div className={`progress-step ${selectedJob.processMap ? 'complete' : 'active'}`}>
                    <div className="step-indicator">
                      {selectedJob.processMap ? (
                        '✓'
                      ) : (
                        <span className="spinner"></span>
                      )}
                    </div>
                    <div className="step-label">Process Map</div>
                    <div className="step-status">{getStepStatus(selectedJob, 'transcription')}</div>
                  </div>
                  <div className={`progress-step ${selectedJob.bottlenecks ? 'complete' : selectedJob.bottlenecksRequested ? 'active' : ''}`}>
                    <div className="step-indicator">
                      {selectedJob.bottlenecks ? (
                        '✓'
                      ) : selectedJob.bottlenecksRequested ? (
                        <span className="spinner"></span>
                      ) : (
                        '2'
                      )}
                    </div>
                    <div className="step-label">Bottlenecks</div>
                    <div className="step-status">{getStepStatus(selectedJob, 'bottlenecks')}</div>
                  </div>
                  <div className={`progress-step ${selectedJob.improvements ? 'complete' : selectedJob.improvementsRequested ? 'active' : ''}`}>
                    <div className="step-indicator">
                      {selectedJob.improvements ? (
                        '✓'
                      ) : selectedJob.improvementsRequested ? (
                        <span className="spinner"></span>
                      ) : (
                        '3'
                      )}
                    </div>
                    <div className="step-label">Improvements</div>
                    <div className="step-status">{getStepStatus(selectedJob, 'improvements')}</div>
                  </div>
                </div>
              </div>
              
              <div className="job-content">
                <section className="process-section">
                  <h3>Process Map</h3>
                  {selectedJob.processMap ? (
                    <div className="text-area">
                      {selectedJob.processMap}
                      <button 
                        className="download-button" 
                        onClick={() => downloadAsMd(selectedJob.runId, 'transcription')}
                      >
                        Download as .md
                      </button>
                    </div>
                  ) : (
                    <div className="processing-message">
                      <span className="spinner-inline"></span>
                      {getStepStatus(selectedJob, 'transcription')}
                    </div>
                  )}
                </section>
                
                <section className="bottlenecks-section">
                  <h3>Bottlenecks</h3>
                  {selectedJob.currentStep >= 2 && !selectedJob.bottlenecks && !selectedJob.bottlenecksRequested && (
                    <button 
                      className="action-button" 
                      onClick={() => identifyBottlenecks(selectedJob.runId)}
                      disabled={loading}
                    >
                      🔍 Identify bottlenecks
                    </button>
                  )}
                  {selectedJob.bottlenecksRequested && !selectedJob.bottlenecks && (
                    <div className="processing-message">
                      <span className="spinner-inline"></span>
                      {getStepStatus(selectedJob, 'bottlenecks')}
                    </div>
                  )}
                  {selectedJob.bottlenecks ? (
                    <div className="text-area">
                      {selectedJob.bottlenecks}
                      <button 
                        className="download-button" 
                        onClick={() => downloadAsMd(selectedJob.runId, 'bottlenecks')}
                      >
                        Download as .md
                      </button>
                    </div>
                  ) : selectedJob.currentStep < 2 ? (
                    <div className="waiting-message">
                      {getStepStatus(selectedJob, 'bottlenecks')}
                    </div>
                  ) : null}
                </section>
                
                <section className="improvements-section">
                  <h3>Improvements</h3>
                  {selectedJob.currentStep >= 3 && !selectedJob.improvements && !selectedJob.improvementsRequested && (
                    <button 
                      className="action-button" 
                      onClick={() => suggestImprovements(selectedJob.runId)}
                      disabled={loading}
                    >
                      💡 Suggest Improvements
                    </button>
                  )}
                  {selectedJob.improvementsRequested && !selectedJob.improvements && (
                    <div className="processing-message">
                      <span className="spinner-inline"></span>
                      {getStepStatus(selectedJob, 'improvements')}
                    </div>
                  )}
                  {selectedJob.improvements ? (
                    <div className="text-area">
                      {selectedJob.improvements}
                      <button 
                        className="download-button" 
                        onClick={() => downloadAsMd(selectedJob.runId, 'improvements')}
                      >
                        Download as .md
                      </button>
                    </div>
                  ) : selectedJob.currentStep < 3 ? (
                    <div className="waiting-message">
                      {getStepStatus(selectedJob, 'improvements')}
                    </div>
                  ) : null}
                </section>
              </div>
            </div>
          )}
        </main>

        <Chat selectedJob={selectedJob} />
      </div>
    </div>
  );
}

export default App;
