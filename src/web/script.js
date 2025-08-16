// Meetup Dashboard - Clean version without dummy data
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing...');
    initializeMeetupIntegration();
});

// Meetup API Integration
function initializeMeetupIntegration() {
    const fetchButton = document.getElementById('fetchMeetupData');
    const refreshButton = document.getElementById('refreshAllData');
    const resultsDiv = document.getElementById('meetupResults');
    const warningDiv = document.getElementById('refreshWarning');
    
    console.log('Elements found:', {
        fetchButton: !!fetchButton,
        refreshButton: !!refreshButton,
        resultsDiv: !!resultsDiv,
        warningDiv: !!warningDiv
    });
    
    if (!fetchButton || !resultsDiv) {
        console.warn('Required meetup elements not found');
        return;
    }
    
    // Refresh All Data button handler
    if (refreshButton) {
        console.log('Adding click handler to refresh button');
        refreshButton.onclick = function() {
            console.log('Refresh button clicked!');
            
            if (refreshButton.disabled) {
                console.log('Button disabled, returning');
                return;
            }
            
            // Show warning
            if (warningDiv) {
                console.log('Showing warning');
                warningDiv.style.display = 'block';
            }
            
            // Confirm action
            if (!confirm('This will refresh all data from Meetup API and may take several minutes. Continue?')) {
                console.log('User cancelled');
                if (warningDiv) warningDiv.style.display = 'none';
                return;
            }
            
            console.log('User confirmed, calling API...');
            callRefreshAPI(refreshButton, warningDiv);
        };
    } else {
        console.log('Refresh button not found!');
    }
    
    // Original fetch button handler
    fetchButton.addEventListener('click', async function() {
        if (fetchButton.disabled) return;
        
        fetchButton.disabled = true;
        fetchButton.classList.add('loading');
        fetchButton.textContent = 'Fetching Data...';
        resultsDiv.classList.remove('show');
        
        console.log('Fetching Meetup data from Lambda...');
        
        try {
            const response = await fetch('https://der8vsst03.execute-api.ap-southeast-2.amazonaws.com/prod/meetup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            });
            
            console.log('Response status:', response.status);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('Response data:', data);
            
            if (data.success) {
                displayMeetupData(data.data);
            } else {
                displayMeetupError(data.error || 'Failed to fetch data');
            }
        } catch (error) {
            console.error('Error fetching Meetup data:', error);
            displayMeetupError(`Network error: ${error.message}`);
        } finally {
            fetchButton.disabled = false;
            fetchButton.classList.remove('loading');
            fetchButton.textContent = 'Load Data';
        }
    });
}

async function callRefreshAPI(refreshButton, warningDiv) {
    try {
        refreshButton.disabled = true;
        refreshButton.textContent = 'Refreshing...';
        
        console.log('Making API call to refresh endpoint');
        const response = await fetch('https://der8vsst03.execute-api.ap-southeast-2.amazonaws.com/prod/pro-network-details', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({})
        });
        
        console.log('Refresh API response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Refresh API response data:', data);
        
        if (data.success) {
            alert('Data refresh initiated successfully! The process may take several minutes to complete.');
        } else {
            alert(`Error: ${data.error || 'Failed to initiate data refresh'}`);
        }
    } catch (error) {
        console.error('Error refreshing data:', error);
        alert(`Network error: ${error.message}`);
    } finally {
        refreshButton.disabled = false;
        refreshButton.textContent = 'Refresh All Data';
        if (warningDiv) warningDiv.style.display = 'none';
    }
}

function displayMeetupData(data) {
    const resultsDiv = document.getElementById('meetupResults');
    
    resultsDiv.innerHTML = `
        <div class="analytics-stats">
            <div class="stat-item">
                <span class="stat-number">${data.totalCountries}</span>
                <div class="stat-label">Countries</div>
            </div>
            <div class="stat-item">
                <span class="stat-number">${data.totalGroups}</span>
                <div class="stat-label">Groups</div>
            </div>
            <div class="stat-item">
                <span class="stat-number">${data.totalMembers.toLocaleString()}</span>
                <div class="stat-label">Members</div>
            </div>
        </div>
    `;
    
    if (data.groups && data.groups.length > 0) {
        displayGroups(data.groups);
    }
}

function displayGroups(groups) {
    const groupsDiv = document.getElementById('groupsResults');
    
    const tableRows = groups.map((group, index) => {
        const foundedDate = group.foundedDate ? new Date(group.foundedDate).toLocaleDateString() : 'N/A';
        const memberCount = group.stats?.memberCounts?.all?.toLocaleString() || 'N/A';
        const eventsCount = group.eventsLast12Months || 0;
        const avgRsvps = group.avgRsvpsLast12Months || 0;
        
        return `
            <tr class="group-row" onclick="toggleGroupDetails('${group.id}', ${index})">
                <td>
                    <span class="expand-icon" id="icon-${index}">▶</span>
                    ${group.name}
                </td>
                <td>${group.country || 'N/A'}</td>
                <td>${foundedDate}</td>
                <td>${memberCount}</td>
                <td>${eventsCount}</td>
                <td>${avgRsvps}</td>
            </tr>
            <tr class="group-details" id="details-${index}" style="display: none;">
                <td colspan="6">
                    <div class="details-content" id="content-${index}">
                        <div class="loading">Loading group details...</div>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
    
    groupsDiv.innerHTML = `
        <table class="groups-table">
            <thead>
                <tr>
                    <th>Group Name</th>
                    <th>Country</th>
                    <th>Founded</th>
                    <th>Members</th>
                    <th>Events (12mo)</th>
                    <th>Avg RSVPs</th>
                </tr>
            </thead>
            <tbody>
                ${tableRows}
            </tbody>
        </table>
    `;
}

function toggleGroupDetails(groupId, index) {
    const detailsRow = document.getElementById(`details-${index}`);
    const icon = document.getElementById(`icon-${index}`);
    const content = document.getElementById(`content-${index}`);
    
    if (detailsRow.style.display === 'none') {
        detailsRow.style.display = 'table-row';
        icon.textContent = '▼';
        
        if (content.innerHTML.includes('Loading')) {
            fetchGroupDetails(groupId, index);
        }
    } else {
        detailsRow.style.display = 'none';
        icon.textContent = '▶';
    }
}

function fetchGroupDetails(groupId, index) {
    const content = document.getElementById(`content-${index}`);
    
    fetch('https://der8vsst03.execute-api.ap-southeast-2.amazonaws.com/prod/group-details', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ groupId: groupId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            displayGroupEvents(data.data, index);
        } else {
            content.innerHTML = `<div class="error">Error: ${data.error || 'Failed to load group details'}</div>`;
        }
    })
    .catch(error => {
        console.error('Error:', error);
        content.innerHTML = `<div class="error">Network error: ${error.message}</div>`;
    });
}

function displayGroupEvents(data, index) {
    const content = document.getElementById(`content-${index}`);
    
    if (data.events && data.events.length > 0) {
        const eventsHtml = data.events.map(event => `
            <div class="event-item">
                <h4>${event.title}</h4>
                <p><strong>Date:</strong> ${event.dateTime ? new Date(event.dateTime).toLocaleDateString() : 'N/A'}</p>
                <p><strong>RSVPs:</strong> ${event.rsvps?.totalCount || 0}</p>
                ${event.eventUrl ? `<p><a href="${event.eventUrl}" target="_blank">View Event</a></p>` : ''}
            </div>
        `).join('');
        
        content.innerHTML = `
            <h4>Past Events (${data.totalPastEvents} total)</h4>
            <div class="events-list">
                ${eventsHtml}
            </div>
        `;
    } else {
        content.innerHTML = `
            <h4>Past Events</h4>
            <p>No past events found for this group.</p>
        `;
    }
}

function displayMeetupError(error) {
    const resultsDiv = document.getElementById('meetupResults');
    
    resultsDiv.innerHTML = `
        <div class="error">
            ${error}
        </div>
    `;
}