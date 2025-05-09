document.addEventListener('DOMContentLoaded', function() {
    // Add a test button to the page
    const searchForm = document.getElementById('search-form');
    const loadingDiv = document.getElementById('loading');
    const resultsContainer = document.getElementById('results-container');
    const resultsInfo = document.getElementById('results-info');
    const resultsList = document.getElementById('results-list');
    const downloadJson = document.getElementById('download-json');
    const downloadCsv = document.getElementById('download-csv');
    
    // Add a test button
    const testButton = document.createElement('button');
    testButton.id = 'test-search-button';
    testButton.textContent = 'Test Simple Search';
    testButton.className = 'test-button';
    testButton.style.backgroundColor = '#4CAF50';
    testButton.style.color = 'white';
    testButton.style.padding = '10px 15px';
    testButton.style.border = 'none';
    testButton.style.borderRadius = '4px';
    testButton.style.cursor = 'pointer';
    testButton.style.marginTop = '10px';
    
    // Insert the button after the search form
    searchForm.parentNode.insertBefore(testButton, searchForm.nextSibling);
    
    // Add click event to the test button
    testButton.addEventListener('click', function() {
        // Show loading spinner
        loadingDiv.style.display = 'block';
        resultsContainer.style.display = 'none';
        
        // Get form data
        const query = document.getElementById('query').value || 'test query';
        const numResults = document.getElementById('num_results').value || 5;
        
        console.log('Sending test request to /api/simple-search');
        console.log('Query:', query);
        console.log('Num results:', numResults);
        
        // Send AJAX request to the simple-search endpoint
        fetch('/api/simple-search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                num_results: numResults
            }),
        })
        .then(response => {
            console.log('Response status:', response.status);
            return response.json();
        })
        .then(data => {
            console.log('Received data:', data);
            
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
            
            // Update download links if available
            if (data.files) {
                downloadJson.href = `/download/${data.files.json}`;
                downloadCsv.href = `/download/${data.files.csv}`;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            loadingDiv.style.display = 'none';
            alert('An error occurred while testing. Please check the console for details.');
        });
    });
});
