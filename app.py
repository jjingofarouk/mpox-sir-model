from flask import Flask, render_template, request, send_file
import numpy as np
from scipy.integrate import odeint
import matplotlib.pyplot as plt
import io
import base64
import pandas as pd
from fpdf import FPDF

app = Flask(__name__)

# SIR Model Function
def sir_model(y, t, N, beta, gamma):
    S, I, R = y
    dSdt = -beta * S * I / N
    dIdt = beta * S * I / N - gamma * I
    dRdt = gamma * I
    return dSdt, dIdt, dRdt

# Route for the home page
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Get user inputs from the form
        N = float(request.form['population'])
        I0 = float(request.form['infected'])
        beta = float(request.form['infection_rate'])
        gamma = float(request.form['recovery_rate'])
        days = int(request.form['days'])

        # Initial conditions
        R0 = 0
        S0 = N - I0 - R0
        y0 = S0, I0, R0

        # Time grid
        t = np.linspace(0, days, days)

        # Solve the SIR model
        ret = odeint(sir_model, y0, t, args=(N, beta, gamma))
        S, I, R = ret.T

        # Calculate summary metrics
        peak_day = np.argmax(I)
        peak_infected = max(I)
        total_recovered = R[-1]
        final_susceptible = S[-1]

        # Plot the results
        plt.figure(figsize=(10, 6))
        plt.plot(t, S / 1e6, 'b', alpha=0.5, lw=2, label='Susceptible')
        plt.plot(t, I / 1e6, 'r', alpha=0.5, lw=2, label='Infected')
        plt.plot(t, R / 1e6, 'g', alpha=0.5, lw=2, label='Recovered')
        plt.xlabel('Time (days)')
        plt.ylabel('Number (millions)')
        plt.title('Mpox SIR Model Simulation')
        plt.legend()
        plt.grid(True)

        # Save the plot to a BytesIO object
        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode('utf8')
        plt.close()

        # Prepare summary data
        summary = {
            "peak_day": peak_day,
            "peak_infected": peak_infected / 1e6,
            "total_recovered": total_recovered / 1e6,
            "final_susceptible": final_susceptible / 1e6,
        }

        return render_template('index.html', plot_url=plot_url, summary=summary)

    return render_template('index.html', plot_url=None, summary=None)

# Route to download results as PDF
@app.route('/download', methods=['POST'])
def download():
    # Generate a PDF report
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Mpox SIR Model Simulation Report", ln=True, align="C")
    pdf.cell(200, 10, txt="---------------------------------", ln=True, align="C")
    pdf.cell(200, 10, txt=f"Peak Infection Day: {request.form['peak_day']}", ln=True)
    pdf.cell(200, 10, txt=f"Peak Infected (Millions): {request.form['peak_infected']}", ln=True)
    pdf.cell(200, 10, txt=f"Total Recovered (Millions): {request.form['total_recovered']}", ln=True)
    pdf.cell(200, 10, txt=f"Final Susceptible (Millions): {request.form['final_susceptible']}", ln=True)
    pdf.output("sir_report.pdf")
    return send_file("sir_report.pdf", as_attachment=True)

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)