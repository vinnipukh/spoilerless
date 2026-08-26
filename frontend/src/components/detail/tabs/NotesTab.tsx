import { useState } from 'react'
import { Skeleton } from '@/components/ui/skeleton'
import type { NoteResponse } from '../../../types/userContent'

// 12-08 (THERMO-P0-04): NoteItem + NoteEditor extracted verbatim from
// DetailPanel.tsx alongside their Notes tab body.

function NoteItem({
  note,
  onEdit,
  onDelete,
  readOnly = false,
}: {
  note: NoteResponse
  onEdit: (note: NoteResponse) => void
  onDelete: (noteId: string) => void
  /** Quick task 260805-te3: read-only (visitor) mode hides edit/delete. */
  readOnly?: boolean
}) {
  const [deleting, setDeleting] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  return (
    <div className="rounded-md border border-border p-2 text-sm">
      <p className="whitespace-pre-wrap break-words">{note.content}</p>
      {!readOnly && (
      <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
        <button
          type="button"
          className="hover:text-foreground transition-colors"
          onClick={() => onEdit(note)}
          aria-label="Edit note"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-4 w-4 inline mr-0.5" aria-hidden="true">
            <path d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
          </svg>
          Edit
        </button>
        <span aria-hidden="true">·</span>
        {confirmDelete ? (
          <span className="flex items-center gap-1">
            <span className="text-destructive">Delete?</span>
            <button
              type="button"
              className="text-destructive hover:text-destructive/80 font-medium transition-colors"
              onClick={() => {
                setDeleting(true)
                onDelete(note.id)
              }}
              disabled={deleting}
              aria-label="Confirm delete note"
            >
              {deleting ? '...' : 'Yes'}
            </button>
            <button
              type="button"
              className="hover:text-foreground transition-colors"
              onClick={(e) => { e.stopPropagation(); setConfirmDelete(false) }}
              aria-label="Cancel delete"
            >
              No
            </button>
          </span>
        ) : (
          <button
            type="button"
            className="hover:text-destructive transition-colors"
            onClick={() => setConfirmDelete(true)}
            aria-label="Delete note"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-4 w-4 inline mr-0.5" aria-hidden="true">
              <path d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
            </svg>
            Delete
          </button>
        )}
      </div>
      )}
    </div>
  )
}

export function NoteEditor({
  initialContent,
  onSave,
  onCancel,
  saving,
}: {
  initialContent: string
  onSave: (content: string) => void
  onCancel: () => void
  saving: boolean
}) {
  const [content, setContent] = useState(initialContent)

  return (
    <div className="flex flex-col gap-2">
      <textarea
        className="w-full min-h-[60px] rounded-md border border-border bg-background p-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="Write a note..."
        aria-label="Note content"
        rows={3}
      />
      <div className="flex items-center gap-2">
        <button
          type="button"
          className="inline-flex items-center justify-center rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 min-h-[44px]"
          onClick={() => onSave(content)}
          disabled={saving || !content.trim()}
          aria-label={saving ? 'Saving...' : 'Save note'}
        >
          {saving ? 'Saving...' : 'Save'}
        </button>
        <button
          type="button"
          className="inline-flex items-center justify-center rounded-md px-3 py-1.5 text-xs font-medium hover:bg-muted transition-colors min-h-[44px]"
          onClick={onCancel}
          disabled={saving}
          aria-label="Cancel"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}

type NotesTabProps = {
  notesState: {
    status: 'loading' | 'error' | 'success'
    data: NoteResponse[]
  }
  notes: NoteResponse[]
  editingNote: NoteResponse | null
  showNewNoteForm: boolean
  saving: boolean
  readOnly: boolean
  setShowNewNoteForm: (show: boolean) => void
  handleCreateNote: (content: string) => Promise<void>
  handleEditNote: (noteId: string, content: string) => Promise<void>
  setEditingNote: (note: NoteResponse | null) => void
  handleDeleteNote: (noteId: string) => Promise<void>
}

export function NotesTab({
  notesState,
  notes,
  editingNote,
  showNewNoteForm,
  saving,
  readOnly,
  setShowNewNoteForm,
  handleCreateNote,
  handleEditNote,
  setEditingNote,
  handleDeleteNote,
}: NotesTabProps) {
  return (
    <div className="flex flex-col gap-2 overflow-y-auto px-4 pb-4 pt-2">
      {/* The Notes trigger itself is hidden in read-only (visitor)
          mode — the notes routes are auth-gated, so a guest can
          never reach this content. */}
      {/* Create note form */}
      {showNewNoteForm ? (
        <NoteEditor
          initialContent=""
          onSave={handleCreateNote}
          onCancel={() => setShowNewNoteForm(false)}
          saving={saving}
        />
      ) : (
        !readOnly && (
        <button
          type="button"
          className="inline-flex items-center justify-center gap-1.5 rounded-md border border-dashed border-border px-3 py-2 text-xs text-muted-foreground hover:text-foreground hover:border-foreground/30 transition-colors min-h-[44px]"
          onClick={() => setShowNewNoteForm(true)}
          aria-label="Add note"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-4 w-4" aria-hidden="true">
            <path d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          Add Note
        </button>
        )
      )}

      {/* Loading state */}
      {notesState.status === 'loading' && (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      )}

      {/* Error state */}
      {notesState.status === 'error' && (
        <div className="rounded-md border border-destructive/20 bg-destructive/5 p-3 text-xs text-destructive">
          Failed to load notes. Try again.
        </div>
      )}

      {/* Empty state */}
      {notesState.status === 'success' && notes.length === 0 && (
        <p className="text-xs text-muted-foreground py-2">No notes yet — add one above.</p>
      )}

      {/* Notes list */}
      {notes.length > 0 && (
        <div className="flex flex-col gap-2 max-h-[40vh] overflow-y-auto">
          {notes.map((note) => (
            editingNote?.id === note.id ? (
              <NoteEditor
                key={note.id}
                initialContent={note.content}
                onSave={(content) => handleEditNote(note.id, content)}
                onCancel={() => setEditingNote(null)}
                saving={saving}
              />
            ) : (
              <NoteItem
                key={note.id}
                note={note}
                onEdit={(n) => setEditingNote(n)}
                onDelete={handleDeleteNote}
                readOnly={readOnly}
              />
            )
          ))}
        </div>
      )}
    </div>
  )
}
