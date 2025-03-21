import { render, screen } from '@testing-library/react';
import Navbar from '../Navbar';

describe('Navbar', () => {
  it('renders the application title', () => {
    render(<Navbar />);
    
    // Check that the application title is in the document
    const title = screen.getByText(/Insurance Report Generator/i);
    expect(title).toBeInTheDocument();
  });

  it('renders navigation links', () => {
    render(<Navbar />);
    
    // Check that the home link exists
    const homeLink = screen.getByRole('link', { name: /home/i });
    expect(homeLink).toBeInTheDocument();
  });
}); 