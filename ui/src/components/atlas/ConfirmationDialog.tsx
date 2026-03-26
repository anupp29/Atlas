import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

interface ConfirmationDialogProps {
  open: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  playbookName: string;
  description: string;
  affectedService: string;
}

export function ConfirmationDialog({
  open,
  onConfirm,
  onCancel,
  playbookName,
  description,
  affectedService,
}: ConfirmationDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={(v) => !v && onCancel()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="text-[15px]">Confirm Approval</AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div className="space-y-3">
              <p className="text-[13px] text-muted-foreground">
                Approve playbook: <span className="font-mono font-medium text-foreground">{playbookName}</span>?
              </p>
              <p className="text-[13px] text-muted-foreground">
                This will execute the following action on <span className="font-medium text-foreground">{affectedService}</span>:
              </p>
              <p className="text-[12px] text-muted-foreground bg-muted/50 p-3 rounded border border-border">
                {description}
              </p>
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel className="text-[13px]">Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            className="bg-accent hover:bg-accent/90 text-accent-foreground text-[13px] font-semibold px-6"
          >
            Confirm Approval
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
