// ============================================================================
// BUS RESERVATION AND FLEET SCHEDULING SYSTEM
// Interactive Client-Side Logic
// ============================================================================

document.addEventListener('DOMContentLoaded', function () {
    // ------------------------------------------------------------------------
    // 1. Interactive Seat Selection
    // ------------------------------------------------------------------------
    const seatItems = document.querySelectorAll('.seat-item:not(.seat-booked)');
    const selectedSeatInput = document.getElementById('selected_seat_id');
    const selectedSeatDisplay = document.getElementById('selected_seat_display');
    const confirmBookingBtn = document.getElementById('confirmBookingBtn');

    if (seatItems.length > 0 && selectedSeatInput) {
        seatItems.forEach(seat => {
            seat.addEventListener('click', function () {
                // Deselect previously selected seat
                seatItems.forEach(s => s.classList.remove('seat-selected'));
                
                // Select clicked seat
                this.classList.add('seat-selected');
                const seatId = this.getAttribute('data-seat-id');
                const seatNum = this.getAttribute('data-seat-number');

                selectedSeatInput.value = seatId;
                if (selectedSeatDisplay) {
                    selectedSeatDisplay.innerText = seatNum;
                }
                if (confirmBookingBtn) {
                    confirmBookingBtn.removeAttribute('disabled');
                }
            });
        });
    }

    // ------------------------------------------------------------------------
    // 2. Passenger Mode Toggle (Existing vs New)
    // ------------------------------------------------------------------------
    const modeRadios = document.querySelectorAll('input[name="passenger_mode"]');
    const existingPassengerBlock = document.getElementById('existingPassengerBlock');
    const newPassengerBlock = document.getElementById('newPassengerBlock');

    if (modeRadios.length > 0 && existingPassengerBlock && newPassengerBlock) {
        modeRadios.forEach(radio => {
            radio.addEventListener('change', function () {
                if (this.value === 'existing') {
                    existingPassengerBlock.style.display = 'block';
                    newPassengerBlock.style.display = 'none';
                    // Toggle required attributes
                    toggleRequired(newPassengerBlock, false);
                } else {
                    existingPassengerBlock.style.display = 'none';
                    newPassengerBlock.style.display = 'block';
                    toggleRequired(newPassengerBlock, true);
                }
            });
        });
    }

    function toggleRequired(container, isRequired) {
        const inputs = container.querySelectorAll('input, select');
        inputs.forEach(input => {
            if (isRequired) {
                input.setAttribute('required', 'required');
            } else {
                input.removeAttribute('required');
            }
        });
    }

    // ------------------------------------------------------------------------
    // 3. Interactive Custom SQL Query Runner (Viva Demo)
    // ------------------------------------------------------------------------
    const runSqlBtn = document.getElementById('runSqlBtn');
    const customSqlInput = document.getElementById('customSqlInput');
    const sqlResultArea = document.getElementById('sqlResultArea');

    if (runSqlBtn && customSqlInput && sqlResultArea) {
        runSqlBtn.addEventListener('click', function () {
            const query = customSqlInput.value.trim();
            if (!query) {
                alert('Please enter a SQL SELECT query.');
                return;
            }

            runSqlBtn.disabled = true;
            runSqlBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Executing...';
            sqlResultArea.innerHTML = '<div class="text-muted p-3">Executing query against MySQL...</div>';

            const formData = new FormData();
            formData.append('custom_sql', query);

            fetch('/sql-demo/execute', {
                method: 'POST',
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                runSqlBtn.disabled = false;
                runSqlBtn.innerHTML = '<i class="bi bi-play-fill"></i> Execute SQL';

                if (!data.success) {
                    sqlResultArea.innerHTML = `
                        <div class="alert alert-danger mb-0">
                            <strong><i class="bi bi-exclamation-triangle-fill"></i> Error:</strong> ${data.error}
                        </div>
                    `;
                    return;
                }

                if (data.rows.length === 0) {
                    sqlResultArea.innerHTML = `
                        <div class="alert alert-info mb-0">
                            Query executed successfully! 0 rows returned.
                        </div>
                    `;
                    return;
                }

                let html = `
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <span class="badge bg-success">${data.count} Rows Returned</span>
                    </div>
                    <div class="table-responsive" style="max-height: 400px; overflow-y: auto;">
                        <table class="table table-bordered table-striped table-hover table-sm">
                            <thead class="table-dark sticky-top">
                                <tr>
                `;
                data.columns.forEach(col => {
                    html += `<th>${col}</th>`;
                });
                html += `</tr></thead><tbody>`;

                data.rows.forEach(row => {
                    html += `<tr>`;
                    data.columns.forEach(col => {
                        const val = row[col] !== null ? row[col] : '<span class="text-muted">NULL</span>';
                        html += `<td>${val}</td>`;
                    });
                    html += `</tr>`;
                });

                html += `</tbody></table></div>`;
                sqlResultArea.innerHTML = html;
            })
            .catch(err => {
                runSqlBtn.disabled = false;
                runSqlBtn.innerHTML = '<i class="bi bi-play-fill"></i> Execute SQL';
                sqlResultArea.innerHTML = `
                    <div class="alert alert-danger mb-0">
                        Network error: ${err.message}
                    </div>
                `;
            });
        });
    }

    // ------------------------------------------------------------------------
    // 4. Auto dismiss flash alerts after 5 seconds
    // ------------------------------------------------------------------------
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert-dismissible');
        alerts.forEach(function(alert) {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        });
    }, 5000);
});
