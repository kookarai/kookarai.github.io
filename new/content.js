// Immediately invoked function to avoid polluting global namespace
(function() {
  // Create the button element
  const fab = document.createElement('button');
  fab.innerText = '🎤';

  // Style the button
  Object.assign(fab.style, {
    position: 'fixed',
    bottom: '20px',
    right: '20px',
    width: '60px',
    height: '60px',
    borderRadius: '50%',
    backgroundColor: '#6200EA',
    color: '#FFFFFF',
    border: 'none',
    fontSize: '36px',
    cursor: 'pointer',
    boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
    zIndex: '1000',
  });

  // Append the button to the body
  document.body.appendChild(fab);

  // Function to evaluate XPath and return the first matching element
  function getElementByXPath(xpath) {
    const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
    return result.singleNodeValue;
  }

  // Add click event listener
  fab.addEventListener('click', () => {
    // Define the XPath to locate the phone number element
    const xpath = '//*[@id="app"]/div[1]/section/section/div[2]/div[3]/div[2]/div/div[1]/div/div[2]/div[2]/div[2]/a/span';

    // Get the element using XPath
    const phoneElement = getElementByXPath(xpath);

    if (phoneElement && phoneElement.textContent.trim() !== '') {
      // Extract the phone number text
      let phoneNumber = phoneElement.textContent.trim();
      phoneNumber = phoneNumber.replace(" ","");
      phoneNumber = phoneNumber.replace("+","");

      // Construct the URL with the phone number as a query parameter
      const url = `https://kookarai.github.io?phone=${encodeURIComponent(phoneNumber)}`;

      // Open the URL in a new tab
      window.open(url, '_blank', 'noopener,noreferrer');
    } else {
      // Handle the case where the phone number element is not found or empty
      alert('Phone number not found on the page.');
    }
  });
})();
