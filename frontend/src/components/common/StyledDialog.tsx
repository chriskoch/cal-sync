import React from 'react';
import { Dialog, DialogProps } from '@mui/material';

interface StyledDialogProps extends Omit<DialogProps, 'PaperProps'> {
  children: React.ReactNode;
}

const styles = {
  paper: {
    elevation: 0,
    sx: {
      borderRadius: 3,
      border: '1px solid',
      borderColor: 'divider',
    },
  },
} as const;

/**
 * StyledDialog - Dialog wrapper with consistent paper styling
 *
 * @example
 * <StyledDialog open={open} onClose={handleClose} maxWidth="md">
 *   <DialogTitle>Title</DialogTitle>
 *   <DialogContent>Content</DialogContent>
 * </StyledDialog>
 */
export const StyledDialog: React.FC<StyledDialogProps> = ({ children, ...rest }) => (
  <Dialog PaperProps={styles.paper} {...rest}>
    {children}
  </Dialog>
);
