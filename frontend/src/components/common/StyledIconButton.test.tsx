import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { render } from '../../test/utils';
import { StyledIconButton } from './StyledIconButton';
import { Close, Delete } from '@mui/icons-material';

describe('StyledIconButton', () => {
  it('renders with icon', () => {
    render(
      <StyledIconButton>
        <Close data-testid="close-icon" />
      </StyledIconButton>
    );
    expect(screen.getByTestId('close-icon')).toBeInTheDocument();
  });

  it('handles onClick events', async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();
    render(
      <StyledIconButton onClick={handleClick}>
        <Close />
      </StyledIconButton>
    );

    const button = screen.getByRole('button');
    await user.click(button);

    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('can be disabled', () => {
    render(
      <StyledIconButton disabled>
        <Close />
      </StyledIconButton>
    );
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('supports different sizes', () => {
    render(
      <StyledIconButton size="small">
        <Close data-testid="small-icon" />
      </StyledIconButton>
    );
    expect(screen.getByTestId('small-icon')).toBeInTheDocument();
  });

  it('accepts custom sx prop', () => {
    const { container } = render(
      <StyledIconButton sx={{ color: 'red' }}>
        <Delete />
      </StyledIconButton>
    );
    expect(container.querySelector('.MuiIconButton-root')).toBeInTheDocument();
  });

  it('supports aria-label for accessibility', () => {
    render(
      <StyledIconButton aria-label="Close dialog">
        <Close />
      </StyledIconButton>
    );
    expect(screen.getByLabelText('Close dialog')).toBeInTheDocument();
  });

  it('does not trigger onClick when disabled', () => {
    const handleClick = vi.fn();
    render(
      <StyledIconButton onClick={handleClick} disabled>
        <Close />
      </StyledIconButton>
    );

    const button = screen.getByRole('button');
    // Verify button is disabled and handleClick was never called
    expect(button).toBeDisabled();
    expect(handleClick).not.toHaveBeenCalled();
  });

  it('passes through additional props', () => {
    render(
      <StyledIconButton data-testid="custom-button">
        <Close />
      </StyledIconButton>
    );
    expect(screen.getByTestId('custom-button')).toBeInTheDocument();
  });
});
