import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { render } from '../../test/utils';
import { LoadingBox } from './LoadingBox';

describe('LoadingBox', () => {
  it('renders CircularProgress spinner', () => {
    const { container } = render(<LoadingBox />);
    const spinner = container.querySelector('.MuiCircularProgress-root');
    expect(spinner).toBeInTheDocument();
  });

  it('renders with custom message', () => {
    render(<LoadingBox message="Loading data..." />);
    expect(screen.getByText('Loading data...')).toBeInTheDocument();
  });

  it('renders without message when no message prop provided', () => {
    const { container } = render(<LoadingBox />);
    const spinner = container.querySelector('.MuiCircularProgress-root');
    expect(spinner).toBeInTheDocument();
    expect(screen.queryByRole('paragraph')).not.toBeInTheDocument();
  });

  it('renders without message when message is empty string', () => {
    const { container } = render(<LoadingBox message="" />);
    const spinner = container.querySelector('.MuiCircularProgress-root');
    expect(spinner).toBeInTheDocument();
    expect(screen.queryByRole('paragraph')).not.toBeInTheDocument();
  });

  it('supports custom spinner size', () => {
    const { container } = render(<LoadingBox size={40} />);
    const spinner = container.querySelector('.MuiCircularProgress-root');
    expect(spinner).toBeInTheDocument();
  });

  it('centers content in a box', () => {
    const { container } = render(<LoadingBox message="Centered loading" />);
    const box = container.querySelector('.MuiBox-root');
    expect(box).toBeInTheDocument();
    expect(screen.getByText('Centered loading')).toBeInTheDocument();
  });

  it('accepts custom sx prop', () => {
    const { container } = render(
      <LoadingBox message="Custom style" sx={{ minHeight: 200 }} />
    );
    expect(container.querySelector('.MuiBox-root')).toBeInTheDocument();
  });
});
