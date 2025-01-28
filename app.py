from flask import Flask, render_template, request, send_file
import numpy as np
from scipy.integrate import odeint
import matplotlib.pyplot as plt
import io
import base64
from fpdf import FPDF

app = Flask(__name__)

# Disease parameters (R0 and recovery rate based on scientific literature)
DISEASE_PARAMS = {
    'covid19': {
        'name': 'COVID-19',
        'default_beta': 0.3,
        'default_gamma': 1/14,  # ~14 days recovery
        'color': 'blue'
    },
    'tuberculosis': {
        'name': 'Tuberculosis',
        'default_beta': 0.2,
        'default_gamma': 1/180,  # ~6 months recovery
        'color': 'red'
    },
    'ebola': {
        'name': 'Ebola',
        'default_beta': 0.4,
        'default_gamma': 1/21,  # ~21 days recovery
        'color': 'green'
    },
    'mpox': {
        'name': 'Mpox',
        'default_beta': 0.2,
        'default_gamma': 1/21,  # ~21 days recovery
        'color': 'purple'
    },
    'influenza': {
        'name': 'Influenza',
        'default_beta': 0.4,
        'default_gamma': 1/7,  # ~7 days recovery
        'color': 'orange'
    }
}

def sir_model(y, t, N, beta, gamma):
    S, I, R = y
    dSdt = -beta * S * I / N
    dIdt = beta * S * I / N - gamma * I
    dRdt = gamma * I
    return dSdt, dIdt, dRdt

def run_simulation(N, I0, beta, gamma, days):
    R0 = 0
    S0 = N - I0 - R0
    y0 = S0, I0, R0
    t = np.linspace(0, days, days)
    ret = odeint(sir_model, y0, t, args=(N, beta, gamma))
    return t, ret.T

def create_plot(simulations, days):
    plt.figure(figsize=(12, 8))
    
    for disease, data in simulations.items():
        t, (S, I, R) = data
        params = DISEASE_PARAMS[disease]
        plt.plot(t, I / 1e6, color=params['color'], alpha=0.7, lw=2, 
                label=f"{params['name']} Infected")

    plt.xlabel('Time (days)')
    plt.ylabel('Number of Infected (millions)')
    plt.title('Disease Spread Comparison')
    plt.legend()
    plt.grid(True)
    
    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    plt.close()
    
    return base64.b64encode(img.getvalue()).decode('utf8')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        N = float(request.form['population'])
        days = int(request.form['days'])
        
        simulations = {}
        summary = {}
        
        for disease in DISEASE_PARAMS:
            if disease in request.form.getlist('diseases'):
                I0 = float(request.form.get(f'{disease}_initial', 100))
                beta = float(request.form.get(f'{disease}_beta', 
                           DISEASE_PARAMS[disease]['default_beta']))
                gamma = float(request.form.get(f'{disease}_gamma', 
                            DISEASE_PARAMS[disease]['default_gamma']))
                
                t, (S, I, R) = run_simulation(N, I0, beta, gamma, days)
                simulations[disease] = (t, (S, I, R))
                
                peak_day = np.argmax(I)
                summary[disease] = {
                    'name': DISEASE_PARAMS[disease]['name'],
                    'peak_day': int(peak_day),
                    'peak_infected': I[peak_day] / 1e6,
                    'total_recovered': R[-1] / 1e6,
                    'final_susceptible': S[-1] / 1e6,
                    'r0': beta/gamma
                }
        
        plot_url = create_plot(simulations, days)
        return render_template('index.html', 
                             plot_url=plot_url, 
                             summary=summary, 
                             diseases=DISEASE_PARAMS)
    
    return render_template('index.html', 
                         plot_url=None, 
                         summary=None, 
                         diseases=DISEASE_PARAMS)

@app.route('/download', methods=['POST'])
def download():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Disease Spread Simulation Report", ln=True, align="C")
    pdf.cell(200, 10, txt="---------------------------------", ln=True, align="C")
    
    for disease in DISEASE_PARAMS:
        if f"{disease}_peak_day" in request.form:
            pdf.cell(200, 10, txt=f"\n{DISEASE_PARAMS[disease]['name']} Results:", ln=True)
            pdf.cell(200, 10, txt=f"Peak Infection Day: {request.form[f'{disease}_peak_day']}", ln=True)
            pdf.cell(200, 10, txt=f"Peak Infected (Millions): {request.form[f'{disease}_peak_infected']}", ln=True)
            pdf.cell(200, 10, txt=f"Total Recovered (Millions): {request.form[f'{disease}_total_recovered']}", ln=True)
            pdf.cell(200, 10, txt=f"Final Susceptible (Millions): {request.form[f'{disease}_final_susceptible']}", ln=True)
            pdf.cell(200, 10, txt=f"Basic Reproduction Number (R0): {request.form[f'{disease}_r0']}", ln=True)
            pdf.cell(200, 10, txt="", ln=True)
    
    pdf.output("disease_simulation_report.pdf")
    return send_file("disease_simulation_report.pdf", as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
