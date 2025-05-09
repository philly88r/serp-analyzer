document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('search-form');
    const loadingDiv = document.getElementById('loading');
    const resultsContainer = document.getElementById('results-container');
    const resultsInfo = document.getElementById('results-info');
    const resultsList = document.getElementById('results-list');
    const downloadJson = document.getElementById('download-json');
    const downloadCsv = document.getElementById('download-csv');
    
    // Create a progress bar element for the loading div
    const progressBarContainer = document.createElement('div');
    progressBarContainer.className = 'progress-container';
    progressBarContainer.innerHTML = `
        <div class="progress">
            <div class="progress-bar" role="progressbar" style="width: 0%" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"></div>
        </div>
        <p class="progress-status">Starting search...</p>
    `;
    loadingDiv.appendChild(progressBarContainer);
    
    // Get progress bar elements
    const progressBar = progressBarContainer.querySelector('.progress-bar');
    const progressStatus = progressBarContainer.querySelector('.progress-status');
    
    // Function to update progress
    function updateProgress(progress, message) {
        progressBar.style.width = `${progress}%`;
        progressBar.setAttribute('aria-valuenow', progress);
        progressStatus.textContent = message || 'Processing...';
    }
    
    // Function to check status of a search operation
    function checkSearchStatus(statusUrl, maxAttempts = 60, interval = 3000) {
        let attempts = 0;
        
        function pollStatus() {
            fetch(statusUrl)
                .then(response => response.json())
                .then(statusData => {
                    // Update progress
                    updateProgress(statusData.progress, statusData.message);
                    
                    if (statusData.status === 'completed') {
                        // Search completed, get the results
                        fetch(`/api/results/${statusData.result_file}`)
                            .then(response => response.json())
                            .then(data => {
                                // Hide loading spinner
                                loadingDiv.style.display = 'none';
                                
                                // Show results
                                resultsContainer.style.display = 'block';
                                
                                // Update results info
                                resultsInfo.innerHTML = `
                                    <p><strong>Query:</strong> ${data.query}</p>
                                    <p><strong>Timestamp:</strong> ${data.timestamp}</p>
                                    <p><strong>Found:</strong> ${data.results.length} results</p>
                                `;
                                
                                // Update results list
                                resultsList.innerHTML = '';
                                data.results.forEach((result, index) => {
                                    const resultItem = document.createElement('div');
                                    resultItem.className = 'result-item';
                                    
                                    // Check if there's an SEO analysis
                                    let seoAnalysisHtml = '';
                                    if (result.seo_analysis) {
                                        seoAnalysisHtml = `
                                            <div class="seo-analysis-toggle">
                                                <button class="btn btn-sm btn-primary toggle-seo-btn">Show SEO Analysis</button>
                                                <div class="seo-analysis-content" style="display: none;">
                                                    <div class="markdown-content">${marked.parse(result.seo_analysis)}</div>
                                                </div>
                                            </div>
                                        `;
                                    }
                                    
                                    resultItem.innerHTML = `
                                        <h3>${index + 1}. ${result.title}</h3>
                                        <p class="result-url"><a href="${result.url}" target="_blank">${result.url}</a></p>
                                        <p class="result-description">${result.meta_description || result.description || 'No description available'}</p>
                                        
                                        <div class="result-details">
                                            <div class="row">
                                                <div class="col-md-4">
                                                    <p><strong>Word Count:</strong> ${result.word_count || 'N/A'}</p>
                                                </div>
                                                <div class="col-md-4">
                                                    <p><strong>Internal Links:</strong> ${result.internal_links_count || 'N/A'}</p>
                                                </div>
                                                <div class="col-md-4">
                                                    <p><strong>External Links:</strong> ${result.external_links_count || 'N/A'}</p>
                                                </div>
                                            </div>
                                        </div>
                                        ${seoAnalysisHtml}
                                    `;
                                    resultsList.appendChild(resultItem);
                                });
                                
                                // Add event listeners for SEO analysis toggles
                                document.querySelectorAll('.toggle-seo-btn').forEach(button => {
                                    button.addEventListener('click', function() {
                                        const content = this.nextElementSibling;
                                        if (content.style.display === 'none') {
                                            content.style.display = 'block';
                                            this.textContent = 'Hide SEO Analysis';
                                        } else {
                                            content.style.display = 'none';
                                            this.textContent = 'Show SEO Analysis';
                                        }
                                    });
                                });
                                
                                // Update download links
                                downloadJson.href = `/download/${data.files.json}`;
                                downloadCsv.href = `/download/${data.files.csv}`;
                            })
                            .catch(error => {
                                console.error('Error fetching results:', error);
                                loadingDiv.style.display = 'none';
                                alert('An error occurred while retrieving results. Please try again.');
                            });
                    } else if (statusData.status === 'error') {
                        // Error occurred
                        loadingDiv.style.display = 'none';
                        alert(`Error: ${statusData.message}`);
                    } else if (attempts < maxAttempts) {
                        // Continue polling
                        attempts++;
                        setTimeout(pollStatus, interval);
                    } else {
                        // Max attempts reached
                        loadingDiv.style.display = 'none';
                        alert('The search operation is taking too long. Please check back later or try again.');
                    }
                })
                .catch(error => {
                    console.error('Error checking status:', error);
                    if (attempts < maxAttempts) {
                        attempts++;
                        setTimeout(pollStatus, interval);
                    } else {
                        loadingDiv.style.display = 'none';
                        alert('An error occurred while checking search status. Please try again.');
                    }
                });
        }
        
        // Start polling
        pollStatus();
    }
    
    searchForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Reset progress
        updateProgress(0, 'Starting search...');
        
        // Show loading spinner
        loadingDiv.style.display = 'block';
        resultsContainer.style.display = 'none';
        
        // Get form data
        const query = document.getElementById('query').value;
        const numResults = document.getElementById('num_results').value;
        
        // Send AJAX request
        fetch('/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                num_results: numResults
            }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.status_url) {
                // Long-running operation, start polling for status
                checkSearchStatus(data.status_url);
            } else {
                // Immediate results (for test queries or mock data)
                // Hide loading spinner
                loadingDiv.style.display = 'none';
                
                // Show results
                resultsContainer.style.display = 'block';
                
                // Update results info
                resultsInfo.innerHTML = `
                    <p><strong>Query:</strong> ${data.query || 'Unknown'}</p>
                    <p><strong>Timestamp:</strong> ${data.timestamp || new Date().toISOString()}</p>
                    <p><strong>Found:</strong> ${data.results && data.results.length ? data.results.length : 0} results</p>
                `;
                
                // Update results list
                resultsList.innerHTML = '';
                
                // Check if we have results
                if (!data.results || data.results.length === 0) {
                    resultsList.innerHTML = `
                        <div class="alert alert-warning">
                            <p><i class="fas fa-exclamation-triangle me-2"></i>No results found or an error occurred.</p>
                            ${data.error ? `<p><strong>Error:</strong> ${data.error}</p>` : ''}
                        </div>
                    `;
                    return;
                }
                
                // Process results
                data.results.forEach((result, index) => {
                    const resultItem = document.createElement('div');
                    resultItem.className = 'result-item';
                    resultItem.innerHTML = `
                        <h3>${index + 1}. ${result.title}</h3>
                        <p class="result-url"><a href="${result.url}" target="_blank">${result.url}</a></p>
                        <p class="result-description">${result.description || 'No description available'}</p>
                    `;
                    resultsList.appendChild(resultItem);
                });
                
                // Update download links
                downloadJson.href = `/download/${data.files.json}`;
                downloadCsv.href = `/download/${data.files.csv}`;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            loadingDiv.style.display = 'none';
            alert('An error occurred while searching. Please try again.');
        });
    });
});