import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { render } from '../../test/utils';
import { StyledTextField } from './StyledTextField';

describe('StyledTextField', () => {
  it('renders with label', () => {
    render(<StyledTextField label="Test Field" />);
    expect(screen.getByLabelText('Test Field')).toBeInTheDocument();
  });

  it('accepts user input', async () => {
    const user = userEvent.setup();
    render(<StyledTextField label="Input Field" />);

    const input = screen.getByLabelText('Input Field');
    await user.type(input, 'Hello World');

    expect(input).toHaveValue('Hello World');
  });

  it('handles onChange events', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(<StyledTextField label="Test" onChange={handleChange} />);

    const input = screen.getByLabelText('Test');
    await user.type(input, 'a');

    expect(handleChange).toHaveBeenCalled();
  });

  it('displays placeholder text', () => {
    render(<StyledTextField label="Test" placeholder="Enter text here" />);
    expect(screen.getByPlaceholderText('Enter text here')).toBeInTheDocument();
  });

  it('can be disabled', () => {
    render(<StyledTextField label="Disabled Field" disabled />);
    expect(screen.getByLabelText('Disabled Field')).toBeDisabled();
  });

  it('supports multiline mode', () => {
    render(<StyledTextField label="Multiline" multiline rows={4} />);
    const textarea = screen.getByLabelText('Multiline');
    expect(textarea.tagName).toBe('TEXTAREA');
  });

  it('displays error state', () => {
    render(
      <StyledTextField
        label="Error Field"
        error
        helperText="This field has an error"
      />
    );
    expect(screen.getByText('This field has an error')).toBeInTheDocument();
  });

  it('supports fullWidth prop', () => {
    const { container } = render(<StyledTextField label="Full Width" fullWidth />);
    const textField = container.querySelector('.MuiTextField-root');
    expect(textField).toBeInTheDocument();
  });

  it('accepts custom sx prop', () => {
    const { container } = render(
      <StyledTextField label="Custom" sx={{ minWidth: 300 }} />
    );
    expect(container.querySelector('.MuiTextField-root')).toBeInTheDocument();
  });

  it('supports required prop', () => {
    render(<StyledTextField label="Required Field" required />);
    const input = screen.getByLabelText(/Required Field/);
    expect(input).toBeRequired();
  });

  it('supports different input types', () => {
    render(<StyledTextField label="Password" type="password" />);
    const input = screen.getByLabelText('Password');
    expect(input).toHaveAttribute('type', 'password');
  });

  it('supports value prop for controlled component', () => {
    render(<StyledTextField label="Controlled" value="Fixed Value" onChange={vi.fn()} />);
    expect(screen.getByLabelText('Controlled')).toHaveValue('Fixed Value');
  });
});
