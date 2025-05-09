
    document.addEventListener('DOMContentLoaded', function() {
        const searchForm = document.getElementById('search-form');
        const loadingDiv = document.getElementById('loading');
        const resultsContainer = document.getElementById('results-container');
        const resultsInfo = document.getElementById('results-info');
        const resultsList = document.getElementById('results-list');
        const downloadJson = document.getElementById('download-json');
        const downloadCsv = document.getElementById('download-csv');
        
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
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
            })
            .catch(error => {
                console.error('Error:', error);
                loadingDiv.style.display = 'none';
                alert('An error occurred while searching. Please try again.');
            });
        });
    });
    