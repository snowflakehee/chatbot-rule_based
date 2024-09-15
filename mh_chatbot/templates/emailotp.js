function sendOTP() {
	const emailInput = document.getElementById('email');
	const otpverify = document.getElementsByClassName('otpverify')[0];

	// Generate a random OTP
	let otp_val = Math.floor(Math.random() * 10000);

	// Prepare the email body
	let emailbody = `<h2>Your OTP is </h2>${otp_val}`;

	// Retrieve multiple email addresses (comma-separated)
	// Example input: "user1@example.com, user2@example.com"
	let emailList = emailInput.value;

	// Send email to multiple recipients
	Email.send({
		SecureToken : "c2aeb6bc-1981-4b21-8f90-af4fb7ec6c4b",
		To : emailList,  // Comma-separated list of email addresses
		From : "2022cs0001@svce.ac.in",
		Subject : "Email OTP using JavaScript",
		Body : emailbody,
	}).then(
		message => {
			if (message === "OK") {
				alert("OTP sent to: " + emailList);
				
				// Show the OTP verification section
				otpverify.style.display = "flex";
				
				const otp_inp = document.getElementById('otp_inp');
				const otp_btn = document.getElementById('otp-btn');

				// Add OTP verification functionality
				otp_btn.addEventListener('click', () => {
					if (otp_inp.value == otp_val) {
						alert("Email address verified...");
					}
					else {
						alert("Invalid OTP");
					}
				});
			} else {
				alert("Failed to send OTP: " + message);
			}
		}
	);
}
