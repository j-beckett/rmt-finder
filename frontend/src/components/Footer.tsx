// No noreferrer, so studiobeckett.ca sees the referral.
export function Footer() {
  return (
    <footer className="mx-auto max-w-3xl px-4">
      <div className="site-footer">
        <a href="https://studiobeckett.ca" target="_blank" rel="noopener">
          A <span className="site-footer-name">Studio Beckett</span> project
        </a>
        <span aria-hidden="true"> · </span>
        <a href="mailto:jen@studiobeckett.ca">
          <span className="site-footer-name">Say hi</span>
        </a>
      </div>
    </footer>
  )
}
