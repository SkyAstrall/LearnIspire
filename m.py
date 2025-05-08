from paywix.payu import Payu
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Configure PayU credentials
payu_config = {
    "merchant_key": "8qyJJz",  # Replace with your actual merchant key
    "merchant_salt": "MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDDcUwnxGLlT/H9o+QwaeLTK3khY0c8j9QwWXlPwo5ollCtnCzut5QppOL4/SlluMliFp09kvYIRagjDNnHPoCS5z6gdWUnjNez5E8TPaa3xXHUQdkZyg6IctnDLd56l+8WI3QQPXT4DYxH2ihvZyjwmVdJLBJIH6i24M8UftE3iklbjuUissMg8MW4jwkSBdYU38wykja/ThV5hvxnqDFDttvukmmeX5Oh67UeuvwIl8xgpXu9BeYzyJQZF1Rf84DhpHhkF3dndfglbAI6orFoiktNpNQzSpc+2OWlIcKsA4G4iJJ5nAysAGkQMzTzme1aI7pC730xAOyxOYOVfPX3AgMBAAECggEBAL1poU/tIZdyCmoyGyXciQr1V/jGubR1BEUzgcGOIew0uc33zQgx/LL7bUm4ORWvp+SbXBrfwfg0YgZOHwXdikhVOrnR7I4PDsH2Y7iXCGuUPIRkqN44mCsfe/KQEs0nUHxZMdPHbAQ3RRwhzwxgoynCwvhUcQdbP2y1pZwMaAF1G8YiFZSpWNlj+8G37QtzIW289VPbVWn6D442KzsTbgGpV1B/7mJt6Z+IBA34O32JYfTQwmPVPRIiYDtMfbPChjeBV7Xiqd1utyfE/f4IT6M0ubkmE88vfZHKiJIBcHYhjLDc2qdACoMhSinW6f8wKtQ+VdG8PAYKdIdgOEofxVkCgYEA/40qKyl+/wFcE0SR2DfuGHx8wimhRSnSijMPISdi5s/Dwl75AZDKwgwUIEqG2WPVZbEx1iiiC1nT7Gqa/GtDkZ0y0YZsDXcDZVX9cl/OpHRgDBF4e+EtikfPIhqbQ8pQUbzy5WZfnsr7CXAP07et0aajo/X/T/sWRiL6TdPZp9UCgYEAw8kfQMzZs5hcXZhfwCwqfsaWYlAJjZfKSWD5Yl66EURnZrr5l4HZZvezfli7FpKy8zaoUS6D+YSvBqBbEkluu40j/50P/z8Pm/IQ1STOx6y44EvM6frCH2AZDuwVq7cRn7EPzrrRub2/GIWucDL2NGQAUIiXC87yRSNZjxqm+JsCgYBfR8/IJgGerHAbEv7Zwgi5Ank1n3XspqpEMsNaVigO7LoNV4G57rVaYkyCuabLmOhwsP9m3OGGH+jfBeRhZtDbkuPmsRrKbmxKtSP5J/WQ5X8GIOFuNsfW/e0hxw/K17zYrP1XQLM4LnAo1aphAuQA/gOXV1npBTIJ1nLC39EQPQKBgFWlXKufMTjUVMuIxZIuf+R3gP++3X74QMB60H1MzP6Sut0AvACgB/d4Mif6LtWAFRI5/cWNoKP9fAddDJniT7Nx2aaPEZlp/60LZnunH2HP2AwefKR6UoMhKbUSZ6R3cBk4fp7DsM0dCURz7kwcrwFaIZ0ZM2IyBF9kSGBGm3YzAoGBAKh1PuaeqLCHg5OVavJD8ccm57dPgS007WD2EiUlylGH4nKsUbofjgeXX4SLZA0Ij/0z4fdlWGbrTiO8xk1Gz33e3VhfmLj/z4CiJMAoGGckifYTMki9i0R7Gn8dc1RJLJipE5DFhe6FjBI2gausLpBsZ9PQvCak1DWlDBiHiCK3",  # Replace with your actual merchant salt
    "success_url": "http://localhost:5000/payment-success",
    "failure_url": "http://localhost:5000/payment-failure",
    "mode": "live",  # Use 'test' for sandbox, 'live' for production
}

# Initialize Payu
payu = Payu(payu_config["merchant_key"], merchant_salt=payu_config["merchant_salt"], mode=payu_config["mode"])


@app.route("/")
def index():
    return render_template("payment_form.html")


@app.route("/process-payment", methods=["POST"])
def process_payment():
    # Transaction data
    transaction_data = {
        "amount": str(1.00),
        "firstname": 'sandeep',
        "email": 'varadasandeep0@gmail.com',
        "phone":'+919391132531',
        "productinfo": 'test',
        "txnid": request.form.get("txnid"),
        'surl': payu_config["success_url"],
        'furl': payu_config["failure_url"],
        'curl': payu_config["failure_url"],
        "udf1": "",
        "udf2": "",
        "udf3": "",
        "udf4": "",
        "udf5": "",
    }
    res = payu.transaction(**transaction_data)
    # Generate PayU form HTML directly
    payu_html = payu.make_html(res)
    print(payu_html)
    # Just return the HTML directly to the browser
    return payu_html


@app.route("/payment-success", methods=["POST"])
def payment_success():
    status = payu.verify_payment(request.form)
    if status:
        return "Payment successful!"
    return "Payment verification failed!"


@app.route("/payment-failure", methods=["POST"])
def payment_failure():
    return "Payment failed or cancelled!"


if __name__ == "__main__":
    app.run(debug=True)
