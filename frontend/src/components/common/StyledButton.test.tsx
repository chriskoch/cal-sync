import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { render } from '../../test/utils';
import {
  PrimaryButton,
  SecondaryButton,
  OutlinedButton,
  DangerButton
} from './StyledButton';
import { PlayArrow } from '@mui/icons-material';

describe('StyledButton', () => {
  describe('PrimaryButton', () => {
    it('renders with text', () => {
      render(<PrimaryButton>Click me</PrimaryButton>);
      expect(screen.getByText('Click me')).toBeInTheDocument();
    });

    it('handles onClick events', async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();
      render(<PrimaryButton onClick={handleClick}>Click me</PrimaryButton>);

      await user.click(screen.getByText('Click me'));
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('renders with startIcon', () => {
      render(
        <PrimaryButton startIcon={<PlayArrow data-testid="play-icon" />}>
          Play
        </PrimaryButton>
      );
      expect(screen.getByTestId('play-icon')).toBeInTheDocument();
      expect(screen.getByText('Play')).toBeInTheDocument();
    });

    it('can be disabled', () => {
      render(<PrimaryButton disabled>Disabled</PrimaryButton>);
      expect(screen.getByText('Disabled')).toBeDisabled();
    });

    it('accepts custom sx prop', () => {
      const { container } = render(
        <PrimaryButton sx={{ minWidth: 200 }}>Custom</PrimaryButton>
      );
      expect(container.querySelector('.MuiButton-root')).toBeInTheDocument();
    });

    it('supports fullWidth prop', () => {
      const { container } = render(
        <PrimaryButton fullWidth>Full Width</PrimaryButton>
      );
      const button = container.querySelector('.MuiButton-root');
      expect(button).toBeInTheDocument();
    });

    it('supports size variants', () => {
      render(<PrimaryButton size="small">Small</PrimaryButton>);
      expect(screen.getByText('Small')).toBeInTheDocument();
    });
  });

  describe('SecondaryButton', () => {
    it('renders with text', () => {
      render(<SecondaryButton>Secondary</SecondaryButton>);
      expect(screen.getByText('Secondary')).toBeInTheDocument();
    });

    it('handles onClick events', async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();
      render(<SecondaryButton onClick={handleClick}>Click me</SecondaryButton>);

      await user.click(screen.getByText('Click me'));
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('can be disabled', () => {
      render(<SecondaryButton disabled>Disabled</SecondaryButton>);
      expect(screen.getByText('Disabled')).toBeDisabled();
    });
  });

  describe('OutlinedButton', () => {
    it('renders with text', () => {
      render(<OutlinedButton>Outlined</OutlinedButton>);
      expect(screen.getByText('Outlined')).toBeInTheDocument();
    });

    it('handles onClick events', async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();
      render(<OutlinedButton onClick={handleClick}>Click me</OutlinedButton>);

      await user.click(screen.getByText('Click me'));
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('renders as outlined variant', () => {
      const { container } = render(<OutlinedButton>Outlined</OutlinedButton>);
      const button = container.querySelector('.MuiButton-outlined');
      expect(button).toBeInTheDocument();
    });
  });

  describe('DangerButton', () => {
    it('renders with text', () => {
      render(<DangerButton>Delete</DangerButton>);
      expect(screen.getByText('Delete')).toBeInTheDocument();
    });

    it('handles onClick events', async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();
      render(<DangerButton onClick={handleClick}>Delete</DangerButton>);

      await user.click(screen.getByText('Delete'));
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('can be disabled', () => {
      render(<DangerButton disabled>Disabled</DangerButton>);
      expect(screen.getByText('Disabled')).toBeDisabled();
    });

    it('renders with startIcon', () => {
      render(
        <DangerButton startIcon={<PlayArrow data-testid="icon" />}>
          Delete
        </DangerButton>
      );
      expect(screen.getByTestId('icon')).toBeInTheDocument();
    });
  });
});
