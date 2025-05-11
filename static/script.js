document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('search-form');
    const loadingDiv = document.getElementById('loading');
    const resultsContainer = document.getElementById('results-container');
    const resultsInfo = document.getElementById('results-info');
    const resultsList = document.getElementById('results-list');
    const downloadJson = document.getElementById('download-json');
    const downloadCsv = document.getElementById('download-csv');
    const viewSerpHtml = document.getElementById('view-serp-html');
    const viewAnalysis = document.getElementById('view-analysis');
    const generateBlog = document.getElementById('generate-blog');
    const generateBlogButton = document.getElementById('generate-blog-button');
    const viewBlogsButton = document.getElementById('view-blogs-button');
    const extractedFacts = document.getElementById('extracted-facts');
    const comparativeTableBody = document.getElementById('comparative-table-body');
    const comparativeTableFooter = document.getElementById('comparative-table-footer');
    const seoRecommendations = document.getElementById('seo-recommendations');
    
    // Charts
    let wordCountChart;
    let linksChart;
    
    // Elements for progress tracking
    const loadingStatus = document.getElementById('loading-status');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const timeoutWarning = document.getElementById('timeout-warning');
    const cancelButton = document.getElementById('cancel-button');
    
    // Track request state
    let currentRequest = null;
    let progressCheckInterval = null;
    let timeoutTimer = null;
    let requestCancelled = false;
    
    // Handle form submission
    searchForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Reset state
        resetAnalysisState();
        
        // Show loading spinner
        loadingDiv.style.display = 'block';
        resultsContainer.style.display = 'none';
        
        // Get form data
        const query = document.getElementById('query').value;
        const numResults = document.getElementById('num_results').value;
        
        // Update progress UI
        loadingStatus.textContent = 'Initiating search for: ' + query;
        progressText.textContent = 'Starting analysis...'; 
        progressBar.style.width = '5%';
        
        // Send AJAX request
        currentRequest = fetch('/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                num_results: numResults
            }),
            // Add signal for abort controller if browser supports it
            signal: window.AbortController ? new AbortController().signal : undefined
        });
        
        // Set timeout warning
        timeoutTimer = setTimeout(() => {
            timeoutWarning.style.display = 'block';
        }, 30000); // Show warning after 30 seconds
        
        // Start progress checking
        let progressStage = 0;
        const progressStages = [
            { percent: 10, text: 'Retrieving search results...' },
            { percent: 20, text: 'Processing search results...' },
            { percent: 30, text: 'Analyzing pages (this may take several minutes)...' },
            { percent: 60, text: 'Extracting SEO metrics...' },
            { percent: 80, text: 'Generating comparative analysis...' },
            { percent: 90, text: 'Finalizing results...' }
        ];
        
        progressCheckInterval = setInterval(() => {
            if (requestCancelled) {
                clearInterval(progressCheckInterval);
                return;
            }
            
            if (progressStage < progressStages.length) {
                const stage = progressStages[progressStage];
                progressBar.style.width = stage.percent + '%';
                progressText.textContent = stage.text;
                progressStage++;
            }
        }, 5000); // Update progress every 5 seconds
        
        // Handle the response
        currentRequest
        .then(response => {
            if (requestCancelled) {
                throw new Error('Request cancelled by user');
            }
            return response.json();
        })
        .then(data => {
            // Clear timers and intervals
            clearTimeout(timeoutTimer);
            clearInterval(progressCheckInterval);
            
            // Update progress to 100%
            progressBar.style.width = '100%';
            progressText.textContent = 'Analysis complete!';
            
            // Hide loading spinner after a short delay
            setTimeout(() => {
                loadingDiv.style.display = 'none';
                
                // Show results
                resultsContainer.style.display = 'block';
                
                // Update results info
                resultsInfo.innerHTML = `
                    <div class="info-grid">
                        <div class="info-item">
                            <h3><i class="fas fa-search"></i> Query</h3>
                            <p>${data.query}</p>
                        </div>
                        <div class="info-item">
                            <h3><i class="fas fa-clock"></i> Timestamp</h3>
                            <p>${formatTimestamp(data.timestamp)}</p>
                        </div>
                        <div class="info-item">
                            <h3><i class="fas fa-list-ol"></i> Results</h3>
                            <p>${data.results && data.results.length ? data.results.length : 0} pages analyzed</p>
                        </div>
                        <div class="info-item">
                            <h3><i class="fas fa-chart-bar"></i> Status</h3>
                            <p>Analysis complete</p>
                        </div>
                    </div>
                `;
                
                // Update download links
                if (data.files) {
                    downloadJson.href = `/download/${data.files.json}`;
                    downloadCsv.href = data.files.csv ? `/download/${data.files.csv}` : '#';
                    viewSerpHtml.href = data.files.serp_html ? `/view/${data.files.serp_html}` : '#';
                    viewAnalysis.href = data.files.seo_analysis ? `/analysis/${data.files.seo_analysis}` : '#';
                }
                
                // Generate comparative table
                if (data.results && Array.isArray(data.results)) {
                    generateComparativeTable(data.results);
                    
                    // Generate charts
                    generateCharts(data.results);
                    
                    // Update detailed results list
                    updateDetailedResults(data.results);
                    
                    // Generate SEO recommendations
                    generateSeoRecommendations(data.results);
                } else {
                    console.warn('No results data available or results is not an array');
                    // Display a message to the user
                    document.getElementById('comparative-table').innerHTML = '<div class="alert alert-warning">No results data available. Please try again with a different query.</div>';
                    document.getElementById('charts-container').innerHTML = '<div class="alert alert-warning">No chart data available.</div>';
                    document.getElementById('detailed-results').innerHTML = '<div class="alert alert-warning">No detailed results available.</div>';
                    document.getElementById('seo-recommendations').innerHTML = '<div class="alert alert-warning">Cannot generate SEO recommendations without results data.</div>';
                }
            }, 1000);
        })
        .catch(error => {
            // Clear timers and intervals
            clearTimeout(timeoutTimer);
            clearInterval(progressCheckInterval);
            
            console.error('Error:', error);
            
            if (!requestCancelled) {
                loadingDiv.style.display = 'none';
                alert('An error occurred while searching: ' + error.message + '. Please try again.');
            }
        });
    });
    
    // Handle cancel button click
    cancelButton.addEventListener('click', function() {
        cancelAnalysis();
    });
    
    // Function to cancel the analysis
    function cancelAnalysis() {
        requestCancelled = true;
        
        // Abort the fetch request if browser supports it
        if (currentRequest && currentRequest.abort) {
            currentRequest.abort();
        }
        
        // Clear timers and intervals
        clearTimeout(timeoutTimer);
        clearInterval(progressCheckInterval);
        
        // Reset UI
        loadingDiv.style.display = 'none';
        timeoutWarning.style.display = 'none';
        
        // Show message
        alert('Analysis cancelled. You can try again with fewer results for faster processing.');
    }
    
    // Function to reset analysis state
    function resetAnalysisState() {
        requestCancelled = false;
        clearTimeout(timeoutTimer);
        clearInterval(progressCheckInterval);
        timeoutWarning.style.display = 'none';
        progressBar.style.width = '0%';
    }
    
    // Format timestamp to a readable date
    function formatTimestamp(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleString();
    }
    
    // Generate the comparative table
    function generateComparativeTable(results) {
        comparativeTableBody.innerHTML = '';
        
        // Calculate SEO scores and prepare data
        const resultsWithScores = results.map((result, index) => {
            // Calculate a simple SEO score based on available metrics
            let seoScore = 0;
            let maxScore = 0;
            
            // Title length (optimal: 50-60 chars)
            if (result.title) {
                maxScore += 10;
                const titleLength = result.title.length;
                if (titleLength >= 50 && titleLength <= 60) {
                    seoScore += 10; // Perfect length
                } else if (titleLength >= 40 && titleLength <= 70) {
                    seoScore += 7; // Good length
                } else if (titleLength > 0) {
                    seoScore += 4; // At least has a title
                }
            }
            
            // Description length (optimal: 150-160 chars)
            if (result.description) {
                maxScore += 10;
                const descLength = result.description.length;
                if (descLength >= 150 && descLength <= 160) {
                    seoScore += 10; // Perfect length
                } else if (descLength >= 120 && descLength <= 180) {
                    seoScore += 7; // Good length
                } else if (descLength > 0) {
                    seoScore += 4; // At least has a description
                }
            }
            
            // H1 tags (optimal: 1)
            const h1Count = result.h1_count || (result.headings && result.headings.h1 ? result.headings.h1.length : 0);
            maxScore += 10;
            if (h1Count === 1) {
                seoScore += 10; // Perfect - exactly one H1
            } else if (h1Count > 1) {
                seoScore += 5; // Not ideal but has H1s
            }
            
            // Word count (optimal: > 300)
            const wordCount = result.word_count || (result.content && result.content.word_count ? result.content.word_count : 0);
            maxScore += 10;
            if (wordCount >= 1000) {
                seoScore += 10; // Excellent content length
            } else if (wordCount >= 600) {
                seoScore += 8; // Very good content length
            } else if (wordCount >= 300) {
                seoScore += 6; // Good content length
            } else if (wordCount > 0) {
                seoScore += 3; // At least has some content
            }
            
            // Images with alt text
            const imagesTotal = result.images_count || (result.images ? result.images.total : 0);
            const imagesWithAlt = result.images_with_alt_count || (result.images ? result.images.with_alt : 0);
            const altTextPercentage = imagesTotal > 0 ? Math.round((imagesWithAlt / imagesTotal) * 100) : 0;
            
            maxScore += 10;
            if (altTextPercentage === 100 && imagesTotal > 0) {
                seoScore += 10; // All images have alt text
            } else if (altTextPercentage >= 80) {
                seoScore += 8; // Most images have alt text
            } else if (altTextPercentage >= 50) {
                seoScore += 5; // Half of images have alt text
            } else if (imagesTotal > 0) {
                seoScore += 2; // Has images but few alt texts
            }
            
            // Schema markup
            const schemaCount = result.schema_count || 0;
            maxScore += 10;
            if (schemaCount >= 2) {
                seoScore += 10; // Multiple schema types
            } else if (schemaCount === 1) {
                seoScore += 7; // At least one schema type
            }
            
            // Internal links
            const internalLinksCount = result.internal_links_count || (result.links ? result.links.internal : 0);
            maxScore += 10;
            if (internalLinksCount >= 10) {
                seoScore += 10; // Excellent internal linking
            } else if (internalLinksCount >= 5) {
                seoScore += 7; // Good internal linking
            } else if (internalLinksCount > 0) {
                seoScore += 3; // At least has some internal links
            }
            
            // Calculate final score as percentage
            const finalScore = maxScore > 0 ? Math.round((seoScore / maxScore) * 100) : 0;
            
            return {
                ...result,
                position: index + 1,
                seo_score: finalScore,
                h1_count: h1Count,
                word_count: wordCount,
                internal_links_count: internalLinksCount,
                external_links_count: result.external_links_count || (result.links ? result.links.external : 0),
                images_count: imagesTotal,
                alt_text_percentage: altTextPercentage,
                schema_count: schemaCount
            };
        });
        
        // Sort by SEO score (highest first)
        resultsWithScores.sort((a, b) => b.seo_score - a.seo_score);
        
        // Add rows to table
        resultsWithScores.forEach(result => {
            const row = document.createElement('tr');
            
            // Extract domain from URL
            let domain = '';
            try {
                domain = new URL(result.url).hostname.replace('www.', '');
            } catch (e) {
                domain = result.url;
            }
            
            // Create score class based on value
            let scoreClass = 'score-low';
            if (result.seo_score >= 80) {
                scoreClass = 'score-high';
            } else if (result.seo_score >= 60) {
                scoreClass = 'score-medium';
            }
            
            row.innerHTML = `
                <td>${result.position}</td>
                <td><a href="${result.url}" target="_blank" title="${result.title}">${domain}</a></td>
                <td>${result.word_count}</td>
                <td>${result.h1_count}</td>
                <td>${result.internal_links_count}</td>
                <td>${result.external_links_count}</td>
                <td>${result.images_count}</td>
                <td>${result.alt_text_percentage}%</td>
                <td>${result.schema_count}</td>
                <td class="${scoreClass}">${result.seo_score}</td>
            `;
            
            comparativeTableBody.appendChild(row);
        });
        
        // Calculate averages for footer
        const avgWordCount = Math.round(resultsWithScores.reduce((sum, r) => sum + r.word_count, 0) / resultsWithScores.length);
        const avgH1Count = Math.round(resultsWithScores.reduce((sum, r) => sum + r.h1_count, 0) / resultsWithScores.length * 10) / 10;
        const avgInternalLinks = Math.round(resultsWithScores.reduce((sum, r) => sum + r.internal_links_count, 0) / resultsWithScores.length);
        const avgExternalLinks = Math.round(resultsWithScores.reduce((sum, r) => sum + r.external_links_count, 0) / resultsWithScores.length);
        const avgImagesCount = Math.round(resultsWithScores.reduce((sum, r) => sum + r.images_count, 0) / resultsWithScores.length);
        const avgAltTextPercentage = Math.round(resultsWithScores.reduce((sum, r) => sum + r.alt_text_percentage, 0) / resultsWithScores.length);
        const avgSchemaCount = Math.round(resultsWithScores.reduce((sum, r) => sum + r.schema_count, 0) / resultsWithScores.length * 10) / 10;
        const avgSeoScore = Math.round(resultsWithScores.reduce((sum, r) => sum + r.seo_score, 0) / resultsWithScores.length);
        
        // Add footer with averages
        comparativeTableFooter.innerHTML = `
            <tr>
                <td colspan="2">Average</td>
                <td>${avgWordCount}</td>
                <td>${avgH1Count}</td>
                <td>${avgInternalLinks}</td>
                <td>${avgExternalLinks}</td>
                <td>${avgImagesCount}</td>
                <td>${avgAltTextPercentage}%</td>
                <td>${avgSchemaCount}</td>
                <td>${avgSeoScore}</td>
            </tr>
        `;
    }
    
    // Generate charts
    function generateCharts(results) {
        // Prepare data for charts
        const labels = results.map((result, index) => {
            try {
                return new URL(result.url).hostname.replace('www.', '');
            } catch (e) {
                return `Result ${index + 1}`;
            }
        });
        
        const wordCounts = results.map(result => {
            return result.word_count || (result.content && result.content.word_count ? result.content.word_count : 0);
        });
        
        const internalLinks = results.map(result => {
            return result.internal_links_count || (result.links ? result.links.internal : 0);
        });
        
        const externalLinks = results.map(result => {
            return result.external_links_count || (result.links ? result.links.external : 0);
        });
        
        // Word count chart
        const wordCountCtx = document.getElementById('word-count-chart').getContext('2d');
        if (wordCountChart) {
            wordCountChart.destroy();
        }
        wordCountChart = new Chart(wordCountCtx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Word Count',
                    data: wordCounts,
                    backgroundColor: 'rgba(52, 152, 219, 0.7)',
                    borderColor: 'rgba(52, 152, 219, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Content Length Comparison'
                    },
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `Words: ${context.raw}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Word Count'
                        }
                    }
                }
            }
        });
        
        // Links chart
        const linksCtx = document.getElementById('links-chart').getContext('2d');
        if (linksChart) {
            linksChart.destroy();
        }
        linksChart = new Chart(linksCtx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Internal Links',
                        data: internalLinks,
                        backgroundColor: 'rgba(46, 204, 113, 0.7)',
                        borderColor: 'rgba(46, 204, 113, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'External Links',
                        data: externalLinks,
                        backgroundColor: 'rgba(231, 76, 60, 0.7)',
                        borderColor: 'rgba(231, 76, 60, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Link Distribution Comparison'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Links'
                        }
                    }
                }
            }
        });
    }
    
    // Update detailed results list
    function updateDetailedResults(results) {
        resultsList.innerHTML = '';
        
        results.forEach((result, index) => {
            const resultItem = document.createElement('div');
            resultItem.className = 'result-item';
            
            // Handle potential missing data
            const wordCount = result.word_count || (result.content && result.content.word_count ? result.content.word_count : 0);
            const h1Count = result.h1_count || (result.headings && result.headings.h1 ? result.headings.h1.length : 0);
            const internalLinksCount = result.internal_links_count || (result.links ? result.links.internal : 0);
            const externalLinksCount = result.external_links_count || (result.links ? result.links.external : 0);
            const imagesTotal = result.images_count || (result.images ? result.images.total : 0);
            const imagesWithAlt = result.images_with_alt_count || (result.images ? result.images.with_alt : 0);
            
            // Create HTML for headings
            let headingsHtml = '';
            if (result.headings) {
                const h1 = result.headings.h1 && result.headings.h1.length > 0 ? result.headings.h1[0] : 'None';
                headingsHtml = `
                    <div class="result-section">
                        <h4><i class="fas fa-heading"></i> Main Heading</h4>
                        <p>${h1}</p>
                    </div>
                `;
            }
            
            // Create HTML for error message if present
            let errorHtml = '';
            if (result.error) {
                errorHtml = `
                    <div class="result-error">
                        <p><strong>Error:</strong> ${result.error}</p>
                    </div>
                `;
            }
            
            resultItem.innerHTML = `
                <h3>${index + 1}. ${result.title || 'No Title'}</h3>
                <p class="result-url"><a href="${result.url}" target="_blank">${result.url}</a></p>
                ${errorHtml}
                <p class="result-description">${result.description || 'No description available'}</p>
                
                ${headingsHtml}
                
                <div class="result-metrics">
                    <span class="metric-badge"><i class="fas fa-file-alt"></i> ${wordCount} words</span>
                    <span class="metric-badge"><i class="fas fa-heading"></i> ${h1Count} H1 tags</span>
                    <span class="metric-badge"><i class="fas fa-link"></i> ${internalLinksCount} internal links</span>
                    <span class="metric-badge"><i class="fas fa-external-link-alt"></i> ${externalLinksCount} external links</span>
                    <span class="metric-badge"><i class="fas fa-image"></i> ${imagesTotal} images (${imagesWithAlt} with alt)</span>
                </div>
            `;
            
            resultsList.appendChild(resultItem);
        });
    }
    
    // Generate SEO recommendations
    function generateSeoRecommendations(results) {
        // Calculate averages for key metrics
        const avgWordCount = Math.round(results.reduce((sum, r) => {
            return sum + (r.word_count || (r.content && r.content.word_count ? r.content.word_count : 0));
        }, 0) / results.length);
        
        // Find the top result (assuming it's the best performer)
        const topResult = [...results].sort((a, b) => {
            const aWordCount = a.word_count || (a.content && a.content.word_count ? a.content.word_count : 0);
            const bWordCount = b.word_count || (b.content && b.content.word_count ? b.content.word_count : 0);
            return bWordCount - aWordCount; // Sort by word count as a simple metric
        })[0];
        
        // Generate recommendations
        let recommendations = `
            <h3>To Outrank Competitors:</h3>
            <ul>
                <li><strong>Content Length:</strong> Aim for at least ${Math.round(avgWordCount * 1.2)} words (20% more than average)</li>
                <li><strong>Heading Structure:</strong> Use a single clear H1 tag and multiple H2/H3 tags for proper content organization</li>
                <li><strong>Internal Linking:</strong> Include at least 10 relevant internal links to strengthen site architecture</li>
                <li><strong>Image Optimization:</strong> Ensure all images have descriptive alt text</li>
                <li><strong>Schema Markup:</strong> Implement schema.org structured data for enhanced SERP features</li>
            </ul>
            
            <h3>Top Competitor Analysis:</h3>
            <p>The top-performing page has ${topResult.word_count || (topResult.content && topResult.content.word_count ? topResult.content.word_count : 0)} words and ${topResult.internal_links_count || (topResult.links ? topResult.links.internal : 0)} internal links.</p>
        `;
        
        seoRecommendations.innerHTML = recommendations;
    }
    
    // Handle blog generation
    function setupBlogGenerationHandlers() {
        // Main generate blog button in the results section
        if (generateBlog) { 
            const blogForm = generateBlog.form; 

            if (!blogForm) {
                console.error("Generate Blog button (id='generate-blog') is not inside a form. Cannot attach handler.");
                return;
            }

            generateBlog.addEventListener('click', function(event) {
                const queryValue = document.getElementById('query').value; 

                generateBlog.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
                generateBlog.disabled = true;

                if (!queryValue) {
                    event.preventDefault(); 
                    alert('Please perform a search first to provide a query for the blog.');
                    return;
                }

                const hiddenQueryInput = blogForm.elements['query']; 
                
                if (hiddenQueryInput) {
                    hiddenQueryInput.value = queryValue;
                } else {
                    event.preventDefault(); 
                    alert('Internal error: The blog query input field is missing from the form.');
                    return;
                }

                // DO NOT call event.preventDefault().
                // Allow the default form submission to proceed.
            });
        }
        
        // Secondary generate blog button in the AI content section
        if (generateBlogButton) {
            generateBlogButton.addEventListener('click', function(e) {
                e.preventDefault();
                const query = document.getElementById('query').value;
                if (!query) {
                    alert('Please perform a search first');
                    return;
                }
                
                generateBlogButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
                generateBlogButton.classList.add('disabled');
                
                fetch(`/generate_blog/${encodeURIComponent(query)}`, {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json'
                    }
                })
                .then(response => {
                    if (response.redirected) {
                        window.location.href = response.url;
                    } else {
                        return response.json().catch(() => response.text());
                    }
                })
                .then(data => {
                    if (data && typeof data === 'object' && data.redirect) {
                        window.location.href = data.redirect;
                    } else {
                        window.location.href = `/view_blog/${encodeURIComponent(query)}`;
                    }
                })
                .catch(error => {
                    console.error('Error generating blog:', error);
                    alert('Error generating blog. Please try again.');
                    generateBlogButton.innerHTML = '<i class="fas fa-blog"></i> Generate AI Blog';
                    generateBlogButton.classList.remove('disabled');
                });
            });
        }
        
        // View blogs button
        if (viewBlogsButton) {
            viewBlogsButton.addEventListener('click', function(e) {
                e.preventDefault();
                const query = document.getElementById('query').value;
                if (!query) {
                    alert('Please perform a search first');
                    return;
                }
                
                window.location.href = `/view_blog/${encodeURIComponent(query)}`;
            });
        }
    }
    
    // Display extracted facts when available
    function displayExtractedFacts(facts) {
        if (!extractedFacts || !facts || facts.length === 0) return;
        
        let factsHtml = '<h4>Extracted Facts</h4><ul class="facts-list">';
        
        facts.forEach(fact => {
            factsHtml += `<li><i class="fas fa-check-circle"></i> ${fact}</li>`;
        });
        
        factsHtml += '</ul>';
        extractedFacts.innerHTML = factsHtml;
    }
    
    // Initialize blog generation handlers
    setupBlogGenerationHandlers();
    
    // Update hidden query inputs for blog generation forms
    function updateQueryInputs() {
        const query = document.getElementById('query').value;
        const blogQueryInput = document.getElementById('blog-query-input');
        const blogQueryInput2 = document.getElementById('blog-query-input2');
        const blogViewInput = document.getElementById('blog-view-input');
        
        if (blogQueryInput) blogQueryInput.value = query;
        if (blogQueryInput2) blogQueryInput2.value = query;
        if (blogViewInput) blogViewInput.value = query;
    }
    
    // Update query inputs when page loads
    updateQueryInputs();
    
    // Update query inputs when query input changes
    document.getElementById('query').addEventListener('input', updateQueryInputs);
    
    // Check for facts in the URL parameters
    function getFactsFromUrl() {
        const urlParams = new URLSearchParams(window.location.search);
        const factsParam = urlParams.get('facts');
        if (factsParam) {
            try {
                const facts = JSON.parse(decodeURIComponent(factsParam));
                displayExtractedFacts(facts);
            } catch (e) {
                console.error('Error parsing facts from URL:', e);
            }
        }
    }
    
    // Check for facts on page load
    getFactsFromUrl();
});