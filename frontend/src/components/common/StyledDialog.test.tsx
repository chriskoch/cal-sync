import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { render } from '../../test/utils';
import { StyledDialog } from './StyledDialog';
import { DialogTitle, DialogContent } from '@mui/material';

describe('StyledDialog', () => {
  it('renders when open', () => {
    render(
      <StyledDialog open onClose={vi.fn()}>
        <DialogTitle>Test Dialog</DialogTitle>
        <DialogContent>Dialog content</DialogContent>
      </StyledDialog>
    );
    expect(screen.getByText('Test Dialog')).toBeInTheDocument();
    expect(screen.getByText('Dialog content')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(
      <StyledDialog open={false} onClose={vi.fn()}>
        <DialogTitle>Hidden Dialog</DialogTitle>
      </StyledDialog>
    );
    expect(screen.queryByText('Hidden Dialog')).not.toBeInTheDocument();
  });

  it('calls onClose when clicking backdrop', async () => {
    const user = userEvent.setup();
    const handleClose = vi.fn();
    render(
      <StyledDialog open onClose={handleClose}>
        <DialogTitle>Test Dialog</DialogTitle>
      </StyledDialog>
    );

    const backdrop = document.querySelector('.MuiBackdrop-root');
    if (backdrop) {
      await user.click(backdrop);
      expect(handleClose).toHaveBeenCalled();
    }
  });

  it('supports maxWidth prop', () => {
    render(
      <StyledDialog open onClose={vi.fn()} maxWidth="sm">
        <DialogTitle>Small Dialog</DialogTitle>
      </StyledDialog>
    );
    expect(screen.getByText('Small Dialog')).toBeInTheDocument();
  });

  it('supports fullWidth prop', () => {
    render(
      <StyledDialog open onClose={vi.fn()} fullWidth>
        <DialogTitle>Full Width Dialog</DialogTitle>
      </StyledDialog>
    );
    expect(screen.getByText('Full Width Dialog')).toBeInTheDocument();
  });

  it('renders with custom PaperProps', () => {
    render(
      <StyledDialog
        open
        onClose={vi.fn()}
        PaperProps={{ 'data-testid': 'custom-paper' } as any}
      >
        <DialogTitle>Custom Paper</DialogTitle>
      </StyledDialog>
    );
    expect(screen.getByTestId('custom-paper')).toBeInTheDocument();
  });

  it('passes through additional Dialog props', () => {
    render(
      <StyledDialog
        open
        onClose={vi.fn()}
        aria-labelledby="dialog-title"
      >
        <DialogTitle id="dialog-title">Accessible Dialog</DialogTitle>
      </StyledDialog>
    );
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-labelledby', 'dialog-title');
  });
});
