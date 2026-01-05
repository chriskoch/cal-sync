import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { render } from '../../test/utils';
import { SmallChip } from './SmallChip';
import { CheckCircle } from '@mui/icons-material';

describe('SmallChip', () => {
  it('renders with label', () => {
    render(<SmallChip label="Test Label" />);
    expect(screen.getByText('Test Label')).toBeInTheDocument();
  });

  it('renders with numeric label', () => {
    render(<SmallChip label={42} />);
    expect(screen.getByText('42')).toBeInTheDocument();
  });

  it('renders with icon', () => {
    render(
      <SmallChip
        label="Success"
        icon={<CheckCircle data-testid="check-icon" />}
      />
    );
    expect(screen.getByTestId('check-icon')).toBeInTheDocument();
    expect(screen.getByText('Success')).toBeInTheDocument();
  });

  describe('variants', () => {
    it('renders default variant', () => {
      const { container } = render(<SmallChip label="Default" variant="default" />);
      const chip = container.querySelector('.MuiChip-root');
      expect(chip).toBeInTheDocument();
    });

    it('renders outlined variant', () => {
      const { container } = render(<SmallChip label="Outlined" variant="outlined" />);
      const chip = container.querySelector('.MuiChip-root');
      expect(chip).toBeInTheDocument();
    });

    it('renders status-success variant', () => {
      const { container } = render(<SmallChip label="Success" variant="status-success" />);
      const chip = container.querySelector('.MuiChip-root');
      expect(chip).toBeInTheDocument();
      expect(screen.getByText('Success')).toBeInTheDocument();
    });

    it('renders status-error variant', () => {
      const { container } = render(<SmallChip label="Error" variant="status-error" />);
      const chip = container.querySelector('.MuiChip-root');
      expect(chip).toBeInTheDocument();
      expect(screen.getByText('Error')).toBeInTheDocument();
    });

    it('renders status-running variant', () => {
      const { container } = render(<SmallChip label="Running" variant="status-running" />);
      const chip = container.querySelector('.MuiChip-root');
      expect(chip).toBeInTheDocument();
      expect(screen.getByText('Running')).toBeInTheDocument();
    });

    it('renders status-inactive variant', () => {
      const { container } = render(<SmallChip label="Inactive" variant="status-inactive" />);
      const chip = container.querySelector('.MuiChip-root');
      expect(chip).toBeInTheDocument();
      expect(screen.getByText('Inactive')).toBeInTheDocument();
    });
  });

  it('accepts custom sx prop', () => {
    const { container } = render(
      <SmallChip
        label="Custom"
        sx={{ minWidth: 100 }}
      />
    );
    const chip = container.querySelector('.MuiChip-root');
    expect(chip).toBeInTheDocument();
  });

  it('passes through additional MUI Chip props', () => {
    const { container } = render(
      <SmallChip
        label="Clickable"
        clickable
        data-testid="clickable-chip"
      />
    );
    expect(screen.getByTestId('clickable-chip')).toBeInTheDocument();
  });
});
